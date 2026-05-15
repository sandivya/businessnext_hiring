"""Message strategy selection and safe draft generation."""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel

from businessnext_agent.schemas import CustomerEvaluation, MessageDraft

logger = logging.getLogger(__name__)


class MessageModelPort(Protocol):
    """Port for LLM-backed message drafting."""

    def draft(self, prompt: str, fallback: str) -> str:
        """Return a safe outreach draft."""


class FakeMessageModel:
    """Deterministic test/local model."""

    def draft(self, prompt: str, fallback: str) -> str:
        return fallback


class DraftOutput(BaseModel):
    """Structured LLM response for one outreach message."""

    body: str


class StrandsBedrockMessageModel:
    """Strands/Bedrock implementation kept behind the port."""

    def __init__(self, agent_factory: Any) -> None:
        self.agent_factory = agent_factory

    def draft(self, prompt: str, fallback: str) -> str:
        try:
            logger.debug("Drafting message with Strands agent")
            agent = self.agent_factory()
            result = agent(prompt, structured_output_model=DraftOutput)
            structured = getattr(result, "structured_output", None)
            if isinstance(structured, DraftOutput):
                return structured.body or fallback
            return self._extract_message(result, fallback)
        except Exception as exc:  # pragma: no cover - exercised with fake failing agents
            # Strands owns transient retry through ModelRetryStrategy; this layer only falls back.
            logger.warning("Message drafting failed after Strands retry: %s", exc, exc_info=True)
            return fallback

    def _extract_message(self, result: Any, fallback: str) -> str:
        message = getattr(result, "message", result)
        if isinstance(message, dict):
            return str(message.get("content") or message.get("body") or fallback)
        if isinstance(message, list):
            return " ".join(str(part) for part in message) or fallback
        return str(message) or fallback


def _first_name(full_name: str) -> str:
    return full_name.split(maxsplit=1)[0]


def _format_amount(amount: float | None) -> str:
    if amount is None:
        return "your available amount"
    return f"{int(amount):,}"


class MessagingPolicy:
    """Select templates and redact sensitive trigger language."""

    sensitive_terms: ClassVar[list[str]] = [
        "hospital",
        "medical",
        "low balance",
        "mutual fund redemption",
        "fd closure",
        "credit card usage",
        "utilization spike",
    ]

    def __init__(self, messaging_rules: dict[str, Any], model: MessageModelPort) -> None:
        self.messaging_rules = messaging_rules
        self.model = model

    def draft_messages(
        self,
        evaluations: list[CustomerEvaluation],
        customers_by_id: dict[str, dict[str, Any]],
        tone_id: str,
        limit: int = 5,
    ) -> list[MessageDraft]:
        drafts: list[MessageDraft] = []
        for evaluation in [item for item in evaluations if item.eligible][:limit]:
            customer = customers_by_id[evaluation.customer_id]
            template = self._select_template(customer, evaluation, tone_id)
            fallback = self._render_template(template["message"], customer, evaluation)
            # Keep a deterministic safe template as fallback whenever the model is unavailable.
            prompt = self._draft_prompt(customer, evaluation, template, fallback)
            body = self._redact(self.model.draft(prompt, fallback))
            drafts.append(
                MessageDraft(
                    customer_id=evaluation.customer_id,
                    tone_id=template["tone"],
                    template_id=template["template_id"],
                    channel=template["channel"],
                    subject=template.get("subject_or_header"),
                    body=body,
                    cta=template["cta"],
                    safety_notes=self._safety_notes(template),
                    source_evidence=[rule.display_name for rule in evaluation.matched_rules[:3]],
                )
            )
            logger.info("Drafted safe message for customer %s", evaluation.customer_id)
        return drafts

    def _select_template(
        self,
        customer: dict[str, Any],
        evaluation: CustomerEvaluation,
        tone_id: str,
    ) -> dict[str, Any]:
        scenario = self._scenario(customer, evaluation)
        templates = self.messaging_rules["message_templates"]
        for template in templates:
            if template["scenario"] == scenario and template["tone"] == tone_id:
                return template
        for template in templates:
            if template["tone"] == tone_id:
                return template
        return next(template for template in templates if template["scenario"] == scenario)

    def _scenario(self, customer: dict[str, Any], evaluation: CustomerEvaluation) -> str:
        activity = customer.get("digital_loan_activity", {})
        service = customer.get("service_interactions", {})
        loan_profile = customer.get("loan_profile", {})
        recent = customer.get("recent_financial_activity", {})
        if activity.get("loan_application_status") == "Started_Not_Submitted":
            return "abandoned_application"
        if service.get("last_loan_related_inquiry_date"):
            return "loan_inquiry_followup"
        if activity.get("emi_calculator_last_used_date"):
            return "emi_calculator_used"
        if evaluation.recommendation.amount:
            return "pre_approved_high_value"
        if loan_profile.get("existing_loan_closure_months_remaining", 99) <= 3:
            return "existing_loan_near_closure"
        if recent.get("fd_closed_last_60d") or recent.get("mf_redeemed_last_60d"):
            return "fd_or_mf_liquidity_context"
        return "salary_day_offer"

    def _render_template(
        self,
        template: str,
        customer: dict[str, Any],
        evaluation: CustomerEvaluation,
    ) -> str:
        rendered = template.replace("{{first_name}}", _first_name(customer["full_name"]))
        rendered = rendered.replace(
            "{{customer_segment}}", str(customer.get("customer_segment", ""))
        )
        rendered = rendered.replace(
            "{{pre_approved_amount}}", _format_amount(evaluation.recommendation.amount)
        )
        rendered = rendered.replace(
            "{{loan_profile.pre_approved_personal_loan_amount}}",
            _format_amount(evaluation.recommendation.amount),
        )
        return rendered

    def _draft_prompt(
        self,
        customer: dict[str, Any],
        evaluation: CustomerEvaluation,
        template: dict[str, Any],
        fallback: str,
    ) -> str:
        return (
            "Draft a concise personal-loan outreach message using the provided safe template. "
            "Do not mention sensitive inferred triggers such as low balance, medical expenses, "
            "fund redemption, FD closure, or card utilization. "
            f"Customer: {customer['full_name']}. "
            f"Tone: {template['tone']}. Channel: {template['channel']}. "
            f"Evidence: {[rule.display_name for rule in evaluation.matched_rules[:3]]}. "
            f"Safe baseline: {fallback}"
        )

    def _redact(self, message: str) -> str:
        redacted = message
        for term in self.sensitive_terms:
            redacted = re.sub(term, "planned expenses", redacted, flags=re.IGNORECASE)
        return redacted

    def _safety_notes(self, template: dict[str, Any]) -> list[str]:
        notes = ["Sensitive inferred triggers were not used directly."]
        if template.get("sensitivity_note"):
            notes.append(template["sensitivity_note"])
        return notes
