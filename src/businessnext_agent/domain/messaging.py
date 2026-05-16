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


def _plural_months(months: Any) -> str:
    try:
        count = int(months)
    except (TypeError, ValueError):
        return ""
    if count <= 0:
        return ""
    return f"{count} month{'s' if count != 1 else ''}"


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
            body = self._safe_draft_body(self.model.draft(prompt, fallback), fallback)
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
        return self._personalized_fallback(rendered, customer, evaluation)

    def _personalized_fallback(
        self,
        baseline: str,
        customer: dict[str, Any],
        evaluation: CustomerEvaluation,
    ) -> str:
        first_name = _first_name(customer["full_name"])
        greeting = "Dear" if baseline.startswith("Dear ") else "Hi"
        relationship = self._relationship_line(customer)
        offer = self._offer_line(evaluation)
        intent = self._intent_line(customer)
        cta = self._cta_line(customer, evaluation)
        lines = [
            f"{greeting} {first_name}, {relationship}",
            f"{offer} {intent}".strip(),
            cta,
        ]
        return "\n".join(line for line in lines if line)

    def _relationship_line(self, customer: dict[str, Any]) -> str:
        segment = customer.get("customer_segment")
        tenure = _plural_months(customer.get("bank_tenure_months"))
        products = customer.get("products_held") or []
        product_text = ""
        if isinstance(products, list) and products:
            product_text = f" and your {products[0].lower()} relationship"
        if segment and tenure:
            return f"as a {segment} customer with {tenure} of banking history{product_text}, your profile stands out for a personal loan conversation."
        if segment:
            return f"as a {segment} customer{product_text}, your profile stands out for a personal loan conversation."
        return "your banking profile stands out for a personal loan conversation."

    def _offer_line(self, evaluation: CustomerEvaluation) -> str:
        amount = evaluation.recommendation.amount
        rate = evaluation.recommendation.rate_pct
        if amount and rate:
            return f"You may be eligible for up to Rs {_format_amount(amount)} with rate options around {rate}%."
        if amount:
            return f"You may be eligible for up to Rs {_format_amount(amount)} with flexible EMI choices."
        return "You can explore personal loan options with flexible EMI choices."

    def _intent_line(self, customer: dict[str, Any]) -> str:
        activity = customer.get("digital_loan_activity", {})
        service = customer.get("service_interactions", {})
        if activity.get("loan_application_status") == "Started_Not_Submitted":
            return "Since your request is already part-way through, we can help you complete it quickly."
        if service.get("last_loan_related_inquiry_date"):
            return "Based on your recent enquiry, an RM can help you compare the available options."
        if activity.get("emi_calculator_last_used_date"):
            return "You can continue from EMI planning and review a tenure that fits your monthly budget."
        try:
            page_sessions = int(activity.get("loan_product_page_sessions_30d") or 0)
        except (TypeError, ValueError):
            page_sessions = 0
        if page_sessions >= 3:
            return "Your recent loan-page activity suggests this may be a good time to review options."
        return "It can be useful for planned expenses without disturbing longer-term goals."

    def _cta_line(self, customer: dict[str, Any], evaluation: CustomerEvaluation) -> str:
        channel = evaluation.recommendation.preferred_channel or customer.get("preferred_contact_channel")
        if channel:
            return f"Would you like us to share the best tenure and EMI choices over {channel}?"
        return "Would you like us to share the best tenure and EMI choices?"

    def _draft_prompt(
        self,
        customer: dict[str, Any],
        evaluation: CustomerEvaluation,
        template: dict[str, Any],
        fallback: str,
    ) -> str:
        return (
            "Draft a customer-ready personal-loan outreach message in 2 to 3 short lines. "
            "Make it catchy but credible, with one personalized detail from relationship, offer, "
            "or safe intent context. Do not include approval instructions, workflow text, markdown, "
            "tokens, placeholders, or explanations. "
            "Do not mention sensitive inferred triggers such as low balance, medical expenses, "
            "fund redemption, FD closure, or card utilization. "
            f"Customer: {customer['full_name']}. "
            f"Segment: {customer.get('customer_segment')}. City: {customer.get('city')}. "
            f"Bank tenure months: {customer.get('bank_tenure_months')}. "
            f"Preferred channel: {customer.get('preferred_contact_channel')}. "
            f"Offer amount: {_format_amount(evaluation.recommendation.amount)}. "
            f"Tone: {template['tone']}. Channel: {template['channel']}. "
            f"Evidence: {[rule.display_name for rule in evaluation.matched_rules[:3]]}. "
            f"Safe baseline: {fallback}"
        )

    def _redact(self, message: str) -> str:
        redacted = message
        for term in self.sensitive_terms:
            redacted = re.sub(term, "planned expenses", redacted, flags=re.IGNORECASE)
        return redacted

    def _safe_draft_body(self, message: str, fallback: str) -> str:
        redacted = self._redact(message).strip()
        if self._looks_like_meta_response(redacted):
            logger.info("Discarded model meta-response and used safe template fallback.")
            return self._redact(fallback).strip()
        return redacted or self._redact(fallback).strip()

    def _looks_like_meta_response(self, message: str) -> bool:
        lowered = message.lower()
        meta_markers = [
            "approval token",
            "approve ",
            "to proceed",
            "ready to generate",
            "receive the final message",
            "draft generation",
        ]
        return any(marker in lowered for marker in meta_markers)

    def _safety_notes(self, template: dict[str, Any]) -> list[str]:
        notes = ["Sensitive inferred triggers were not used directly."]
        if template.get("sensitivity_note"):
            notes.append(template["sensitivity_note"])
        return notes
