"""Strands-decorated tools for the loan outreach agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from strands import tool

from businessnext_agent.schemas import AgentRequest

if TYPE_CHECKING:
    from businessnext_agent.application.workflow import WorkflowService


def build_workflow_tools(service: WorkflowService) -> list[Any]:
    """Expose the workflow capabilities as Strands tools."""

    @tool(
        name="show_capabilities",
        description="Show what the personal-loan outreach agent can do.",
    )
    def show_capabilities(session_id: str | None = None) -> dict[str, Any]:
        return service.handle(AgentRequest(session_id=session_id, prompt="help")).model_dump(
            mode="json"
        )

    @tool(
        name="show_customer_field_catalog",
        description="Show customer fields grouped for non-technical campaign users.",
    )
    def show_customer_field_catalog(session_id: str | None = None) -> dict[str, Any]:
        return service.handle(
            AgentRequest(session_id=session_id, prompt="show available fields")
        ).model_dump(mode="json")

    @tool(
        name="show_available_checks",
        description="Show hard filters and weighted scoring checks available for shortlisting.",
    )
    def show_available_checks(session_id: str | None = None) -> dict[str, Any]:
        return service.handle(AgentRequest(session_id=session_id, prompt="show checks")).model_dump(
            mode="json"
        )

    @tool(
        name="show_message_styles",
        description="Show outreach message styles and tones available to the user.",
    )
    def show_message_styles(session_id: str | None = None) -> dict[str, Any]:
        return service.handle(
            AgentRequest(session_id=session_id, prompt="show message styles")
        ).model_dump(mode="json")

    @tool(
        name="run_workflow_prompt",
        description="Run a user prompt through the governed HITL workflow.",
    )
    def run_workflow_prompt(prompt: str, session_id: str | None = None) -> dict[str, Any]:
        return service.handle(AgentRequest(session_id=session_id, prompt=prompt)).model_dump(
            mode="json"
        )

    return [
        show_capabilities,
        show_customer_field_catalog,
        show_available_checks,
        show_message_styles,
        run_workflow_prompt,
    ]
