"""Governed tool-routing layer for the prompt-first agent."""

from __future__ import annotations

import logging
from typing import Any

from businessnext_agent.orchestration.planner import HybridPlanner, PlannerPort
from businessnext_agent.orchestration.policy import AgentPolicy
from businessnext_agent.schemas import AgentPlan, AgentRequest, AgentResponse, WorkflowEvent

logger = logging.getLogger(__name__)


class GovernedAgentOrchestrator:
    """Route user turns through governed tools without bypassing HITL policy."""

    def __init__(
        self,
        service: Any,
        planner: PlannerPort | None = None,
        policy: AgentPolicy | None = None,
    ) -> None:
        self.service = service
        self.planner = HybridPlanner(planner)
        self.policy = policy or AgentPolicy()

    def handle(self, request: AgentRequest) -> AgentResponse:
        plan = self.plan(request)
        logger.info(
            "Agentic route selected",
            extra={
                "intent": plan.intent,
                "tool_name": plan.tool_name,
                "rationale": plan.rationale,
                "risk_flags": plan.risk_flags,
            },
        )
        self._audit_plan(request.session_id, plan)
        response = self._execute(plan, request.session_id)
        response.structured_result = {
            **response.structured_result,
            "agentic_route": self.policy.route_metadata(plan),
        }
        return response

    def plan(self, request: AgentRequest) -> AgentPlan:
        """Create a bounded plan from the prompt and session state."""

        return self.policy.validate_plan(self.planner.plan(request), request.prompt)

    def _execute(self, plan: AgentPlan, session_id: str | None) -> AgentResponse:
        tools = self._tool_map()
        if plan.tool_name in tools:
            if plan.tool_name == "run_workflow_prompt":
                result = tools[plan.tool_name](prompt=plan.prompt, session_id=session_id)
            else:
                result = tools[plan.tool_name](session_id=session_id)
            return AgentResponse.model_validate(result)
        return self.service.handle(AgentRequest(session_id=session_id, prompt=plan.prompt))

    def _tool_map(self) -> dict[str, Any]:
        if not hasattr(self.service, "strands_tools"):
            return {}
        return {tool.tool_name: tool for tool in self.service.strands_tools()}

    def _audit_plan(self, session_id: str | None, plan: AgentPlan) -> None:
        store = getattr(self.service, "store", None)
        if store is None or not session_id:
            return
        store.add_event(
            session_id,
            WorkflowEvent(
                event_type="agentic_route_selected",
                message="Selected governed agent route.",
                payload=self.policy.route_metadata(plan),
            ),
        )
