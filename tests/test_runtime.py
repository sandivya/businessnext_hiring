from __future__ import annotations

from businessnext_agent import runtime
from businessnext_agent.config import Settings
from businessnext_agent.runtime import build_service, invoke
from businessnext_agent.schemas import AgentRequest, AgentResponse, ResponseStatus


def test_runtime_invoke_with_injected_service(service) -> None:
    response = invoke(
        {"prompt": "help", "request_id": "REQ1", "trace_id": "TRACE1"},
        service=service,
    )
    assert response["status"] == ResponseStatus.COMPLETED
    assert response["session_id"]
    assert response["structured_result"]["observability"]["request_id"] == "REQ1"
    assert response["structured_result"]["observability"]["trace_id"] == "TRACE1"
    assert response["structured_result"]["observability"]["latency_ms"] >= 0


def test_build_service_with_live_adapter_without_calling_aws(settings: Settings) -> None:
    live_settings = settings.model_copy(update={"use_fake_model": False})
    service = build_service(live_settings)
    try:
        response = service.handle(
            __import__("businessnext_agent.schemas").schemas.AgentRequest(prompt="help")
        )
        assert response.status == ResponseStatus.COMPLETED
    finally:
        service.store.close()


def test_runtime_closes_owned_service(monkeypatch) -> None:
    class FakeService:
        def __init__(self) -> None:
            self.closed = False

        def handle(self, request: AgentRequest):
            return AgentResponse(
                session_id="owned",
                status=ResponseStatus.COMPLETED,
                message=f"handled {request.prompt}",
            )

        def close(self):
            self.closed = True

    fake = FakeService()

    def fake_service_factory() -> FakeService:
        return fake

    monkeypatch.setattr(runtime, "build_service", fake_service_factory)
    response = runtime.invoke({"prompt": "help"})
    assert response["message"] == "handled help"
    assert fake.closed is True


def test_runtime_error_response_and_close_warning(monkeypatch) -> None:
    class FailingCloseService:
        def handle(self, request: AgentRequest):
            raise RuntimeError("boom")

        def close(self):
            raise RuntimeError("close boom")

    def failing_service_factory() -> FailingCloseService:
        return FailingCloseService()

    monkeypatch.setattr(runtime, "build_service", failing_service_factory)
    response = runtime.invoke({"session_id": "S1", "prompt": "help"})
    assert response["status"] == ResponseStatus.ERROR
    assert response["session_id"] == "S1"
    assert response["structured_result"]["error_type"] == "RuntimeError"

    invalid = runtime.invoke("bad payload")
    assert invalid["status"] == ResponseStatus.ERROR
    assert invalid["session_id"] == "unavailable"
    assert invalid["structured_result"]["observability"]["request_id"]


def test_model_retry_strategy_uses_settings(settings: Settings) -> None:
    retry = runtime.build_model_retry_strategy(
        settings.model_copy(
            update={
                "model_retry_max_attempts": 4,
                "model_retry_initial_delay_seconds": 1,
                "model_retry_max_delay_seconds": 9,
            }
        )
    )
    assert vars(retry)["_max_attempts"] == 4
    assert vars(retry)["_initial_delay"] == 1
    assert vars(retry)["_max_delay"] == 9


def test_orchestrator_agent_and_tool_registry(settings: Settings, service, monkeypatch) -> None:
    def fake_agent_factory(settings_arg: Settings, tools=None):
        return [tool.tool_name for tool in tools]

    monkeypatch.setattr(runtime, "default_strands_agent_factory", fake_agent_factory)
    names = runtime.build_orchestrator_agent(settings, service)
    assert set(names) >= {
        "show_capabilities",
        "show_customer_field_catalog",
        "show_available_checks",
        "show_message_styles",
        "run_workflow_prompt",
    }

    tools = {tool.tool_name: tool for tool in service.strands_tools()}
    result = tools["show_capabilities"](session_id=None)
    assert result["status"] == ResponseStatus.COMPLETED
    fields = tools["show_customer_field_catalog"](session_id=result["session_id"])
    assert fields["structured_result"]["fields"]
    checks = tools["show_available_checks"](session_id=result["session_id"])
    assert checks["structured_result"]["checks"]
    styles = tools["show_message_styles"](session_id=result["session_id"])
    assert styles["structured_result"]["styles"]
    workflow = tools["run_workflow_prompt"](
        prompt="Find premium customers in Mumbai", session_id=result["session_id"]
    )
    assert workflow["status"] == ResponseStatus.NEEDS_APPROVAL
