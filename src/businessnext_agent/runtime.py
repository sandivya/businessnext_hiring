"""AgentCore-compatible runtime assembly."""

from __future__ import annotations

import logging
import time
from typing import Any

from businessnext_agent.application.workflow import WorkflowService
from businessnext_agent.config import Settings, get_settings
from businessnext_agent.domain.messaging import (
    FakeMessageModel,
    MessagingPolicy,
    StrandsBedrockMessageModel,
)
from businessnext_agent.infrastructure.observability import (
    configure_structured_logging,
    log_context,
    new_request_id,
)
from businessnext_agent.infrastructure.repository import SQLiteStore
from businessnext_agent.orchestration.agent_tools import build_workflow_tools
from businessnext_agent.orchestration.router import GovernedAgentOrchestrator
from businessnext_agent.schemas import AgentRequest, AgentResponse, ResponseStatus, WorkflowEvent

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    """Configure root logging once for local runs and AgentCore containers."""

    configure_structured_logging(settings.log_level)


def build_model_retry_strategy(settings: Settings) -> Any:
    """Use Strands' retry interface for live model throttling and transient failures."""

    from strands import ModelRetryStrategy

    return ModelRetryStrategy(
        max_attempts=settings.model_retry_max_attempts,
        initial_delay=settings.model_retry_initial_delay_seconds,
        max_delay=settings.model_retry_max_delay_seconds,
    )


def load_agent_system_prompt(settings: Settings) -> str:
    """Load the Strands system prompt used by live agent instances."""

    try:
        return settings.agent_system_prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            "Agent system prompt file not found: %s",
            settings.agent_system_prompt_path,
            extra={"error_type": "FileNotFoundError"},
        )
        return (
            "You are a governed personal-loan outreach agent. Follow human approval "
            "requirements, use configured tools, and never bypass compliance checks."
        )


def default_strands_agent_factory(
    settings: Settings,
    tools: list[Any] | None = None,
) -> Any:  # pragma: no cover - AWS integration
    """Create the live Strands Bedrock agent lazily, only when drafting is approved."""

    from strands import Agent
    from strands.agent.conversation_manager import SlidingWindowConversationManager
    from strands.models import BedrockModel
    from strands.types.agent import ConcurrentInvocationMode

    logger.info("Creating Strands Bedrock agent for model %s", settings.bedrock_model_id)
    model = BedrockModel(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
        temperature=0.2,
        max_tokens=700,
    )
    return Agent(
        model=model,
        tools=tools,
        system_prompt=load_agent_system_prompt(settings),
        callback_handler=None,
        conversation_manager=SlidingWindowConversationManager(
            window_size=settings.conversation_window_size,
            per_turn=settings.conversation_management_per_turn,
        ),
        agent_id=settings.agent_id,
        name=settings.agent_name,
        description=settings.agent_description,
        state={
            "domain": "banking_personal_loan",
            "approval_policy": "explicit_token_required",
            "compliance_mode": "deterministic_workflow_controls",
        },
        trace_attributes={
            "app": "businessnext_personal_loan_agent",
            "runtime": "agentcore",
            "model_id": settings.bedrock_model_id,
            "tool_count": len(tools or []),
        },
        retry_strategy=build_model_retry_strategy(settings),
        concurrent_invocation_mode=ConcurrentInvocationMode.THROW,
    )


def build_orchestrator_agent(settings: Settings, service: WorkflowService) -> Any:
    """Build a Strands agent with first-class workflow tools."""

    return default_strands_agent_factory(settings, build_workflow_tools(service))


def build_service(settings: Settings | None = None) -> WorkflowService:
    """Build the transport-neutral workflow service."""

    resolved = settings or get_settings()
    configure_logging(resolved)
    logger.info("Building workflow service with SQLite database %s", resolved.database_path)
    store = SQLiteStore(resolved.database_path)
    store.seed_from_files(resolved)
    messaging_rules = store.get_rules("messaging")
    model = (
        FakeMessageModel()
        if resolved.use_fake_model
        else StrandsBedrockMessageModel(lambda: default_strands_agent_factory(resolved))
    )
    return WorkflowService(store, MessagingPolicy(messaging_rules, model))


def invoke(payload: dict[str, Any], service: WorkflowService | None = None) -> dict[str, Any]:
    """AgentCore entrypoint-compatible function."""

    created_service = service is None
    active_service: WorkflowService | None = None
    started_at = time.perf_counter()
    session_id = (
        str(payload.get("session_id") or "unavailable")
        if isinstance(payload, dict)
        else "unavailable"
    )
    request_id = _payload_text(payload, "request_id") or new_request_id()
    trace_id = _payload_text(payload, "trace_id") or request_id
    with log_context(request_id=request_id, trace_id=trace_id, session_id=session_id):
        try:
            logger.info(
                "Agent invocation started",
                extra={
                    "operation": "agent.invoke",
                    "prompt_length": _prompt_length(payload),
                },
            )
            request = AgentRequest.model_validate(payload)
            active_service = service or build_service()
            response = GovernedAgentOrchestrator(active_service).handle(request)
            result = response.model_dump(mode="json")
            latency_ms = _elapsed_ms(started_at)
            _attach_observability(result, request_id, trace_id, latency_ms)
            logger.info(
                "Agent invocation completed",
                extra={
                    "operation": "agent.invoke",
                    "session_id": response.session_id,
                    "status": response.status,
                    "latency_ms": latency_ms,
                    "event_count": len(response.events),
                },
            )
            return result
        except Exception as exc:
            latency_ms = _elapsed_ms(started_at)
            logger.exception(
                "Agent invocation failed",
                extra={
                    "operation": "agent.invoke",
                    "latency_ms": latency_ms,
                    "error_type": type(exc).__name__,
                },
            )
            result = AgentResponse(
                session_id=session_id,
                status=ResponseStatus.ERROR,
                message=(
                    "I could not complete that request because of an internal error. "
                    "Please retry or ask for help."
                ),
                suggested_prompts=["help", "show fields"],
                events=[
                    WorkflowEvent(
                        event_type="error",
                        message="Agent invocation failed.",
                        payload={"error_type": type(exc).__name__},
                    )
                ],
                structured_result={"error_type": type(exc).__name__},
            ).model_dump(mode="json")
            _attach_observability(result, request_id, trace_id, latency_ms)
            return result
        finally:
            if created_service and active_service is not None:
                try:
                    active_service.close()
                except Exception as exc:
                    logger.warning(
                        "Failed to close workflow service cleanly: %s",
                        exc,
                        extra={"error_type": type(exc).__name__},
                    )


def _payload_text(payload: Any, key: str) -> str | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    return str(value) if value else None


def _prompt_length(payload: Any) -> int:
    prompt = payload.get("prompt") if isinstance(payload, dict) else ""
    return len(str(prompt or ""))


def _elapsed_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1000)


def _attach_observability(
    result: dict[str, Any],
    request_id: str,
    trace_id: str,
    latency_ms: int,
) -> None:
    structured_result = dict(result.get("structured_result") or {})
    structured_result["observability"] = {
        "request_id": request_id,
        "trace_id": trace_id,
        "latency_ms": latency_ms,
    }
    result["structured_result"] = structured_result
