"""LLM-backed planner that generates bounded, policy-validated plans."""

from __future__ import annotations

import json
import logging

from businessnext_agent.domain.messaging import MessageModelPort
from businessnext_agent.schemas import AgentPlan, AgentRequest

logger = logging.getLogger(__name__)


class BedrockPlanner:
    """Use Bedrock to generate structured planning via Strands."""

    def __init__(self, model: MessageModelPort) -> None:
        self.model = model

    def plan(self, request: AgentRequest) -> AgentPlan:
        """Generate a plan using the LLM model."""
        system_prompt = self._system_prompt()
        user_prompt = self._user_prompt(request)
        fallback_json = self._fallback_plan_json(request)

        try:
            response = self.model.draft(
                f"{system_prompt}\n\nUser query: {user_prompt}",
                fallback_json,
            )
            plan_dict = json.loads(response)
            plan = AgentPlan.model_validate(plan_dict)
            logger.info("LLM planner produced valid plan with intent %s", plan.intent)
            return plan
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "LLM planner failed to produce valid plan: %s. Falling back to deterministic planner.",
                exc,
                exc_info=True,
            )
            raise

    def _system_prompt(self) -> str:
        """Return the system prompt for LLM planning."""
        return (
            "You are a governed agent planner for a personal-loan banking campaign system. "
            "Your job is to classify user intents and route them to appropriate tools. "
            "Generate ONLY valid JSON — no markdown, explanations, or meta-response text.\n\n"
            "Valid intents: capability_discovery, field_catalog, check_catalog, message_style_catalog, "
            "workflow_reset, approval_continuation, campaign_workflow.\n"
            "Tool names map 1:1 to intents: "
            "capability_discovery → show_capabilities, "
            "field_catalog → show_customer_field_catalog, "
            "check_catalog → show_available_checks, "
            "message_style_catalog → show_message_styles, "
            "workflow_reset → run_workflow_prompt, "
            "approval_continuation → run_workflow_prompt, "
            "campaign_workflow → run_workflow_prompt.\n\n"
            "Return a JSON object with keys: "
            "intent (string, one of the above), "
            "tool_name (string, corresponding to intent), "
            "prompt (string, normalized user request), "
            "rationale (string, brief reason for routing), "
            "extracted_filters (object, optional keywords like segment, city, credit_score_min)."
        )

    def _user_prompt(self, request: AgentRequest) -> str:
        """Build the user prompt for the LLM."""
        session_info = (
            f"Session {request.session_id}" if request.session_id else "New session"
        )
        return f"[{session_info}]\n{request.prompt}"

    def _fallback_plan_json(self, request: AgentRequest) -> str:
        """Return a safe fallback plan as JSON string."""
        plan = AgentPlan(
            intent="campaign_workflow",
            tool_name="run_workflow_prompt",
            prompt=request.prompt,
            rationale="Fallback plan when LLM planning is unavailable.",
        )
        return plan.model_dump_json()


