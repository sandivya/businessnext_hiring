"""Agent policy checks that constrain planning and tool execution."""

from __future__ import annotations

import re
from typing import Any

from businessnext_agent.schemas import AgentPlan

INTENT_TOOLS = {
    "capability_discovery": "show_capabilities",
    "field_catalog": "show_customer_field_catalog",
    "check_catalog": "show_available_checks",
    "message_style_catalog": "show_message_styles",
    "workflow_reset": "run_workflow_prompt",
    "approval_continuation": "run_workflow_prompt",
    "campaign_workflow": "run_workflow_prompt",
}

SENSITIVE_DIRECTIVES = (
    "ignore approval",
    "skip approval",
    "bypass approval",
    "ignore consent",
    "ignore dnd",
    "contact everyone",
    "include dnd",
    "include excluded",
)


class AgentPolicy:
    """Validate plans before any tool executes."""

    def validate_plan(self, plan: AgentPlan, original_prompt: str) -> AgentPlan:
        risk_flags = list(plan.risk_flags)
        prompt_lower = original_prompt.lower()
        for directive in SENSITIVE_DIRECTIVES:
            if directive in prompt_lower:
                risk_flags.append(f"blocked_directive:{directive.replace(' ', '_')}")
        expected_tool = INTENT_TOOLS[plan.intent]
        if plan.tool_name != expected_tool:
            risk_flags.append("tool_intent_mismatch")
            plan = plan.model_copy(update={"tool_name": expected_tool})
        if plan.intent == "approval_continuation" and not self.has_approval_token(original_prompt):
            risk_flags.append("invalid_approval_format")
        return plan.model_copy(update={"risk_flags": sorted(set(risk_flags))})

    def has_approval_token(self, prompt: str) -> bool:
        return bool(re.search(r"\bapprove\s+[a-z0-9-]{4,}\b", prompt.lower()))

    def route_metadata(self, plan: AgentPlan) -> dict[str, Any]:
        return {
            "intent": plan.intent,
            "tool_name": plan.tool_name,
            "rationale": plan.rationale,
            "extracted_filters": plan.extracted_filters,
            "risk_flags": plan.risk_flags,
        }
