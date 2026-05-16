"""Structured planning for governed tool routing."""

from __future__ import annotations

import re
from typing import Protocol

from businessnext_agent.schemas import AgentPlan, AgentRequest


class PlannerPort(Protocol):
    """Optional model-backed planner interface."""

    def plan(self, request: AgentRequest) -> AgentPlan:
        """Return a schema-valid plan."""


class DeterministicPlanner:
    """Fallback planner that produces bounded, auditable plans."""

    def plan(self, request: AgentRequest) -> AgentPlan:
        prompt = request.prompt.strip()
        prompt_lower = prompt.lower()
        if not prompt_lower or prompt_lower in {
            "help",
            "what can you do",
            "show options",
            "capabilities",
        }:
            return self._plan(
                "capability_discovery",
                "show_capabilities",
                "help",
                "The user asked for help or sent an empty prompt.",
            )
        if self._looks_like_approval(prompt_lower):
            return self._plan(
                "approval_continuation",
                "run_workflow_prompt",
                prompt,
                "Approval turns must continue the governed workflow state machine.",
            )
        if self._looks_like_reset(prompt_lower):
            return self._plan(
                "workflow_reset",
                "run_workflow_prompt",
                prompt,
                "The user is restarting the workflow.",
            )
        if self._asks_for_fields(prompt_lower):
            return self._plan(
                "field_catalog",
                "show_customer_field_catalog",
                "show available fields",
                "The user is asking what customer data is available.",
            )
        if self._asks_for_checks(prompt_lower):
            return self._plan(
                "check_catalog",
                "show_available_checks",
                "show checks",
                "The user is asking about eligibility or scoring checks.",
            )
        if self._asks_for_message_styles(prompt_lower):
            return self._plan(
                "message_style_catalog",
                "show_message_styles",
                "show message styles",
                "The user is asking about outreach tone or format options.",
            )
        normalized = self._normalize_campaign_prompt(prompt)
        return self._plan(
            "campaign_workflow",
            "run_workflow_prompt",
            normalized,
            "The user is asking for customer selection, ranking, or outreach planning.",
            self._extract_filters(normalized.lower()),
        )

    def _plan(
        self,
        intent: str,
        tool_name: str,
        prompt: str,
        rationale: str,
        extracted_filters: dict | None = None,
    ) -> AgentPlan:
        return AgentPlan(
            intent=intent,
            tool_name=tool_name,
            prompt=prompt,
            rationale=rationale,
            extracted_filters=extracted_filters or {},
        )

    def _looks_like_approval(self, prompt_lower: str) -> bool:
        return bool(re.search(r"\bapprove\s+[a-z0-9-]{4,}\b", prompt_lower))

    def _looks_like_reset(self, prompt_lower: str) -> bool:
        return any(
            phrase in prompt_lower
            for phrase in (
                "start over",
                "start again",
                "new shortlist",
                "reset",
                "go back",
                "restart",
            )
        )

    def _asks_for_fields(self, prompt_lower: str) -> bool:
        return any(
            phrase in prompt_lower
            for phrase in (
                "show field",
                "what field",
                "available field",
                "customer field",
                "data field",
                "available data",
                "data do you have",
                "dataset schema",
                "columns",
                "attributes",
            )
        )

    def _asks_for_checks(self, prompt_lower: str) -> bool:
        return any(
            phrase in prompt_lower
            for phrase in (
                "show check",
                "what check",
                "available check",
                "show rule",
                "scoring rule",
                "eligibility",
                "hard filter",
                "scoring logic",
            )
        )

    def _asks_for_message_styles(self, prompt_lower: str) -> bool:
        return any(
            phrase in prompt_lower
            for phrase in (
                "message style",
                "message format",
                "message tone",
                "outreach tone",
                "tone template",
                "message template",
                "outreach template",
                "outreach style",
            )
        )

    def _normalize_campaign_prompt(self, prompt: str) -> str:
        normalized = prompt.strip()
        replacements = {
            "cibil": "credit score",
            "cibil score": "credit score",
            "top customers": "high-value customers",
        }
        for source, target in replacements.items():
            normalized = re.sub(source, target, normalized, flags=re.IGNORECASE)
        return normalized

    def _extract_filters(self, prompt_lower: str) -> dict[str, str | int]:
        filters: dict[str, str | int] = {}
        for segment in ("premium", "preferred", "mass affluent", "mass"):
            if segment in prompt_lower:
                filters["segment"] = segment
        city_match = re.search(r"\bin\s+([a-z]+)\b", prompt_lower)
        if city_match:
            filters["city"] = city_match.group(1)
        score_match = re.search(r"(?:credit score|bureau score)\D+(\d{3})", prompt_lower)
        if score_match:
            filters["credit_score_min"] = int(score_match.group(1))
        return filters


class HybridPlanner:
    """Use a model-backed planner when available, then validate fallback behavior."""

    def __init__(self, model_planner: PlannerPort | None = None) -> None:
        self.model_planner = model_planner
        self.fallback = DeterministicPlanner()

    def plan(self, request: AgentRequest) -> AgentPlan:
        if self.model_planner is None:
            return self.fallback.plan(request)
        try:
            return self.model_planner.plan(request)
        except Exception:
            return self.fallback.plan(request)
