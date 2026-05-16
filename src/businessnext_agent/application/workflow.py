"""Transport-neutral conversational workflow service."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date
from typing import Any

from businessnext_agent.domain.catalog import (
    EXAMPLE_PROMPTS,
    available_field_names,
    capability_message,
    check_catalog,
    field_catalog,
    message_style_catalog,
)
from businessnext_agent.domain.messaging import MessagingPolicy
from businessnext_agent.domain.rules import ScoringEngine
from businessnext_agent.infrastructure.repository import SQLiteStore
from businessnext_agent.schemas import (
    AgentRequest,
    AgentResponse,
    ApprovalStep,
    ResponseStatus,
    SessionState,
    WorkflowEvent,
)

CHECK_ID_PATTERN = re.compile(r"\b(?:HF|INT|CRD|TRG|REL|TIM)\d{3}\b", re.IGNORECASE)
CUSTOMER_ID_PATTERN = re.compile(r"\bCUST\d{4}\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:lakh|lac|crore|cr)?\b|\b\d{2,9}\b")
logger = logging.getLogger(__name__)


class WorkflowService:
    """Owns session flow, approvals, scoring, messaging, and frontend-ready events."""

    def __init__(self, store: SQLiteStore, messaging_policy: MessagingPolicy) -> None:
        self.store = store
        self.messaging_policy = messaging_policy

    def handle(self, request: AgentRequest) -> AgentResponse:
        state = self.store.get_session(request.session_id)
        state.last_prompt = request.prompt
        prompt = request.prompt.strip()
        prompt_lower = prompt.lower()
        logger.info("Handling prompt for session %s", state.session_id)
        if not prompt or self._is_help(prompt_lower):
            response = self._capabilities(state)
        elif self._is_field_catalog(prompt_lower):
            response = self._fields(state, prompt_lower)
        elif self._is_check_catalog(prompt_lower):
            response = self._checks(state)
        elif self._is_message_style_catalog(prompt_lower):
            response = self._message_styles(state)
        elif state.pending_step and (
            self._is_approval(prompt_lower, state.approval_token)
            or (
                state.pending_step == ApprovalStep.MESSAGE_STYLE
                and self._has_approval_token(prompt_lower, state.approval_token)
                and self._extract_tone(prompt_lower)
            )
        ):
            response = self._continue_after_approval(state, prompt_lower)
        elif state.pending_step:
            response = self._pending_reminder(state)
        else:
            response = self._start_workflow(state, prompt_lower)
        self.store.save_session(state)
        logger.info("Session %s completed turn with status %s", state.session_id, response.status)
        return response

    def _capabilities(self, state: SessionState) -> AgentResponse:
        state.has_seen_capabilities = True
        event = self._event(
            state,
            "capabilities_shown",
            "Showed the agent capability guide.",
            {"examples": EXAMPLE_PROMPTS},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.COMPLETED,
            message=capability_message(),
            suggested_prompts=EXAMPLE_PROMPTS,
            events=[event],
            structured_result={
                "field_categories": list(field_catalog().keys()),
                "message_style_count": len(
                    message_style_catalog(self.store.get_rules("messaging"))
                ),
            },
        )

    def _fields(self, state: SessionState, prompt_lower: str) -> AgentResponse:
        unavailable = self._requested_missing_fields(prompt_lower)
        payload = {"fields": field_catalog(), "unavailable_fields": unavailable}
        event = self._event(
            state, "fields_catalog_shown", "Showed available customer fields.", payload
        )
        message = "Here are the customer fields grouped in business language."
        if unavailable:
            message += (
                " I could not find these requested fields: "
                f"{', '.join(unavailable)}. Try asking with one of the listed fields instead."
            )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.COMPLETED,
            message=message,
            suggested_prompts=["Show checks", "Find high-value customers", "Show message styles"],
            events=[event],
            structured_result=payload,
        )

    def _checks(self, state: SessionState) -> AgentResponse:
        checks = check_catalog(self.store.get_rules("shortlisting"))
        event = self._event(
            state, "checks_catalog_shown", "Showed available checks.", {"checks": checks}
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.COMPLETED,
            message="These are the eligibility and scoring checks I can run.",
            suggested_prompts=["Run recommended checks", "Show message styles"],
            events=[event],
            structured_result={"checks": checks},
        )

    def _message_styles(self, state: SessionState) -> AgentResponse:
        styles = message_style_catalog(self.store.get_rules("messaging"))
        event = self._event(
            state,
            "message_styles_shown",
            "Showed available message styles.",
            {"styles": styles},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.COMPLETED,
            message="These message styles are available for outreach.",
            suggested_prompts=[
                "Use warm assisted",
                "Use premium exclusive",
                "Find high-value customers",
            ],
            events=[event],
            structured_result={"styles": styles},
        )

    def _start_workflow(self, state: SessionState, prompt_lower: str) -> AgentResponse:
        missing = self._requested_missing_fields(prompt_lower)
        selected_ids = self._select_customers(prompt_lower)
        selection_summary = self._selection_summary(prompt_lower, selected_ids)
        if not selected_ids:
            logger.info("No customers matched prompt criteria for session %s", state.session_id)
            event = self._event(
                state,
                "needs_clarification",
                "No customers matched the requested criteria.",
                {"selection_summary": selection_summary, "missing_fields": missing},
            )
            return AgentResponse(
                session_id=state.session_id,
                status=ResponseStatus.NEEDS_CLARIFICATION,
                message=(
                    "I could not find customers matching those criteria. "
                    "Try broadening the request or ask me to show available fields."
                ),
                suggested_prompts=["show fields", "Find high-value customers"],
                events=[event],
                structured_result={
                    "workflow_stage": "cohort_selection",
                    "customer_count": 0,
                    "selection_summary": selection_summary,
                    "missing_fields": missing,
                },
            )
        state.selected_customer_ids = selected_ids
        state.selection_summary = selection_summary
        logger.info("Selected %s customers for session %s", len(selected_ids), state.session_id)
        token = self._set_pending(state, ApprovalStep.CUSTOMER_SELECTION)
        payload = {
            "workflow_stage": "cohort_selection",
            "customer_count": len(selected_ids),
            "selection_summary": selection_summary,
            "missing_fields": missing,
        }
        event = self._event(
            state,
            "approval_requested",
            "Requested approval for customer selection.",
            {"step": ApprovalStep.CUSTOMER_SELECTION, **payload},
        )
        message = (
            f"I found {len(selected_ids)} customers to evaluate. "
            f"{selection_summary} "
            "I will rank them by eligibility, intent, relationship value, and timing signals."
        )
        if missing:
            message += f" I could not find these requested fields: {', '.join(missing)}."
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.NEEDS_APPROVAL,
            message=message,
            suggested_prompts=[f"approve {token}", "show fields", "show checks"],
            approval_token=token,
            events=[event],
            structured_result=payload,
        )

    def _continue_after_approval(self, state: SessionState, prompt_lower: str) -> AgentResponse:
        step = state.pending_step
        if step == ApprovalStep.CHECK_SELECTION:
            selected = self._extract_check_ids(prompt_lower)
            if selected:
                logger.info("User selected scoring checks: %s", selected)
                state.selected_check_ids = selected
        if step == ApprovalStep.MESSAGE_STYLE:
            state.chosen_tone_id = self._extract_tone(prompt_lower) or self._recommended_tone()
        self._clear_pending(state)
        if step == ApprovalStep.CUSTOMER_SELECTION:
            return self._after_customer_selection(state)
        if step == ApprovalStep.CHECK_SELECTION:
            return self._after_check_selection(state)
        if step == ApprovalStep.SHORTLIST_ACCEPTANCE:
            return self._after_shortlist_acceptance(state)
        if step == ApprovalStep.MESSAGE_STYLE:
            return self._after_message_style(state, prompt_lower)
        if step == ApprovalStep.BEDROCK_DRAFTING:
            return self._after_bedrock_drafting(state)
        return self._after_final_messages(state)

    def _after_customer_selection(self, state: SessionState) -> AgentResponse:
        checks = check_catalog(self.store.get_rules("shortlisting"))
        state.selected_check_ids = [check["rule_id"] for check in checks]
        token = self._set_pending(state, ApprovalStep.CHECK_SELECTION)
        event = self._event(
            state,
            "checks_proposed",
            "Proposed all configured hard filters and scoring checks.",
            {"check_count": len(state.selected_check_ids), "checks": checks},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.NEEDS_APPROVAL,
            message=(
                f"I recommend running all {len(state.selected_check_ids)} configured checks: "
                "mandatory hard filters first, then weighted scoring. "
                "Use the check selector to narrow optional scoring checks."
            ),
            suggested_prompts=[f"approve {token}", "show checks"],
            approval_token=token,
            events=[event],
            structured_result={"workflow_stage": "check_selection", "checks": checks},
        )

    def _after_check_selection(self, state: SessionState) -> AgentResponse:
        customers = [
            self.store.get_customer(customer_id) for customer_id in state.selected_customer_ids
        ]
        valid_customers = [customer for customer in customers if customer is not None]
        engine = self._scoring_engine(set(state.selected_check_ids))
        evaluations = engine.rank(valid_customers)
        eligible_evaluations = [item for item in evaluations if item.eligible]
        excluded_summary = [
            {
                "customer_id": item.customer_id,
                "name": item.full_name,
                "failed_hard_filters": [rule.display_name for rule in item.failed_hard_filters],
                "failed_checks": [rule.model_dump() for rule in item.failed_hard_filters],
            }
            for item in evaluations
            if not item.eligible
        ][:5]
        logger.info(
            "Ranked %s customers with %s selected checks; %s eligible",
            len(evaluations),
            len(state.selected_check_ids),
            len(eligible_evaluations),
        )
        state.evaluations = evaluations
        token = self._set_pending(state, ApprovalStep.SHORTLIST_ACCEPTANCE)
        summary = [
            {
                "customer_id": item.customer_id,
                "name": item.full_name,
                "score": item.score,
                "priority": item.priority_band,
                "likelihood_pct": item.heuristic_likelihood_pct,
                "recommended_channel": item.recommendation.preferred_channel,
                "offer_amount": item.recommendation.amount,
                "next_action": item.recommendation.suggested_action,
                "reason_codes": [rule.display_name for rule in item.matched_rules[:3]],
                "passed_checks": [rule.model_dump() for rule in item.matched_rules],
                "failed_checks": [rule.model_dump() for rule in item.failed_hard_filters],
            }
            for item in eligible_evaluations[:5]
        ]
        event = self._event(
            state,
            "customers_evaluated",
            "Evaluated and ranked customers.",
            {
                "top_customers": summary,
                "excluded_count": len([item for item in evaluations if not item.eligible]),
                "excluded_customers": excluded_summary,
                "selected_check_ids": state.selected_check_ids,
            },
        )
        if not summary:
            return AgentResponse(
                session_id=state.session_id,
                status=ResponseStatus.NEEDS_CLARIFICATION,
                message=(
                    "I could not produce an eligible shortlist from the selected customers "
                    "and checks. Customers that failed mandatory hard filters were excluded "
                    "from outreach."
                ),
                suggested_prompts=["Start a new shortlist", "show fields"],
                events=[event],
                structured_result={
                    "top_customers": [],
                    "workflow_stage": "shortlist_review",
                    "excluded_count": len([item for item in evaluations if not item.eligible]),
                    "excluded_customers": excluded_summary,
                    "selected_check_ids": state.selected_check_ids,
                },
            )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.NEEDS_APPROVAL,
            message=(
                "I evaluated the customers and ranked the strongest candidates. "
                f"The top result is {summary[0]['name']} with score {summary[0]['score']} "
                f"and likelihood {summary[0]['likelihood_pct']}%."
            ),
            suggested_prompts=[f"approve {token}", "show message styles"],
            approval_token=token,
            events=[event],
            structured_result={
                "top_customers": summary,
                "workflow_stage": "shortlist_review",
                "excluded_count": len([item for item in evaluations if not item.eligible]),
                "excluded_customers": excluded_summary,
                "selected_check_ids": state.selected_check_ids,
            },
        )

    def _after_shortlist_acceptance(self, state: SessionState) -> AgentResponse:
        styles = message_style_catalog(self.store.get_rules("messaging"))
        recommended = self._recommended_tone()
        token = self._set_pending(state, ApprovalStep.MESSAGE_STYLE)
        event = self._event(
            state,
            "message_styles_shown",
            "Requested message style approval.",
            {"styles": styles, "recommended_tone_id": recommended},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.NEEDS_APPROVAL,
            message=(
                "Choose a message style before drafting. "
                f"I recommend '{recommended}'."
            ),
            suggested_prompts=[f"approve {token}", "warm_assisted", "premium_exclusive"],
            approval_token=token,
            events=[event],
            structured_result={
                "workflow_stage": "message_style",
                "styles": styles,
                "recommended_tone_id": recommended,
            },
        )

    def _after_message_style(self, state: SessionState, prompt_lower: str) -> AgentResponse:
        state.chosen_tone_id = state.chosen_tone_id or self._recommended_tone()
        token = self._set_pending(state, ApprovalStep.BEDROCK_DRAFTING)
        event = self._event(
            state,
            "approval_requested",
            "Requested approval before Bedrock message drafting.",
            {"step": ApprovalStep.BEDROCK_DRAFTING, "tone_id": state.chosen_tone_id},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.NEEDS_APPROVAL,
            message=(
                f"I will use the '{state.chosen_tone_id}' style. "
                "Drafting uses the Bedrock model adapter and follows the safety rules."
            ),
            suggested_prompts=[f"approve {token}", "show message styles"],
            approval_token=token,
            events=[event],
            structured_result={
                "workflow_stage": "draft_generation",
                "tone_id": state.chosen_tone_id,
            },
        )

    def _after_bedrock_drafting(self, state: SessionState) -> AgentResponse:
        customers = {
            customer["customer_id"]: customer
            for customer in self.store.list_customers()
            if customer["customer_id"] in {item.customer_id for item in state.evaluations}
        }
        state.message_drafts = self.messaging_policy.draft_messages(
            state.evaluations,
            customers,
            state.chosen_tone_id or self._recommended_tone(),
        )
        logger.info("Generated %s message drafts", len(state.message_drafts))
        token = self._set_pending(state, ApprovalStep.FINAL_MESSAGES)
        event = self._event(
            state,
            "messages_drafted",
            "Drafted personalized outreach messages.",
            {"draft_count": len(state.message_drafts)},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.NEEDS_APPROVAL,
            message=(
                f"I drafted {len(state.message_drafts)} messages and kept sensitive triggers out."
            ),
            suggested_prompts=[f"approve {token}"],
            approval_token=token,
            events=[event],
            structured_result={
                "workflow_stage": "final_approval",
                "drafts": [draft.model_dump() for draft in state.message_drafts],
            },
        )

    def _after_final_messages(self, state: SessionState) -> AgentResponse:
        event = self._event(
            state,
            "workflow_completed",
            "Final messages approved.",
            {"draft_count": len(state.message_drafts)},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.COMPLETED,
            message="The workflow is complete. The approved message drafts are ready for outreach.",
            suggested_prompts=["Start a new shortlist", "Show message styles"],
            events=[event],
            structured_result={
                "workflow_stage": "completed",
                "drafts": [draft.model_dump() for draft in state.message_drafts],
            },
        )

    def _pending_reminder(self, state: SessionState) -> AgentResponse:
        event = self._event(
            state,
            "approval_requested",
            "Reminded user about pending approval.",
            {"step": state.pending_step, "approval_token": state.approval_token},
        )
        return AgentResponse(
            session_id=state.session_id,
            status=ResponseStatus.NEEDS_APPROVAL,
            message=(
                f"I am waiting for approval for '{state.pending_step}'."
            ),
            suggested_prompts=[f"approve {state.approval_token}"],
            approval_token=state.approval_token,
            events=[event],
            structured_result={"pending_step": state.pending_step},
        )

    def _select_customers(self, prompt_lower: str) -> list[str]:
        customers = self.store.list_customers()
        explicit_customer_ids = self._extract_customer_ids(prompt_lower)
        if explicit_customer_ids:
            available_ids = {customer["customer_id"].upper() for customer in customers}
            return [
                customer_id for customer_id in explicit_customer_ids if customer_id in available_ids
            ]
        segments = self._requested_segments(prompt_lower)
        if segments:
            customers = [
                customer
                for customer in customers
                if str(customer.get("customer_segment", "")).lower() in segments
            ]
        cities = self._requested_cities(prompt_lower)
        if cities:
            customers = [
                customer for customer in customers if customer.get("city", "").lower() in cities
            ]
        employment = self._requested_employment(prompt_lower)
        if employment:
            customers = [
                customer
                for customer in customers
                if str(customer.get("employment_type", "")).lower() in employment
            ]
        relationship_threshold = self._threshold_after(
            prompt_lower,
            ["relationship value", "total relationship value"],
        )
        if "high-value" in prompt_lower or "high value" in prompt_lower:
            relationship_threshold = relationship_threshold or 300000
        if relationship_threshold is not None:
            customers = [
                customer
                for customer in customers
                if customer.get("total_relationship_value", 0) >= relationship_threshold
            ]
        bureau_threshold = self._threshold_after(
            prompt_lower, ["bureau score", "credit score", "cibil"]
        )
        if bureau_threshold is not None:
            customers = [
                customer
                for customer in customers
                if customer.get("credit_profile", {}).get("bureau_score") is not None
                and customer["credit_profile"]["bureau_score"] >= bureau_threshold
            ]
        if "loan intent" in prompt_lower or "likely to convert" in prompt_lower:
            customers = [customer for customer in customers if self._has_loan_intent(customer)]
        return [customer["customer_id"] for customer in customers]

    def _selection_summary(self, prompt_lower: str, selected_ids: list[str]) -> str:
        parts = []
        if segments := self._requested_segments(prompt_lower):
            parts.append(f"segment in {', '.join(sorted(segments))}")
        if cities := self._requested_cities(prompt_lower):
            parts.append(f"city in {', '.join(sorted(cities))}")
        if "high-value" in prompt_lower or "high value" in prompt_lower:
            parts.append("high relationship value")
        if "loan intent" in prompt_lower or "likely to convert" in prompt_lower:
            parts.append("loan intent signals")
        criteria = "; ".join(parts) if parts else "all loaded customers"
        return f"Selected {len(selected_ids)} customers using: {criteria}."

    def _scoring_engine(self, enabled_rule_ids: set[str] | None = None) -> ScoringEngine:
        metadata = self.store.get_metadata("customers")
        as_of = date.fromisoformat(metadata.get("generated_on", date.today().isoformat()))
        return ScoringEngine(self.store.get_rules("shortlisting"), as_of, enabled_rule_ids)

    def _requested_missing_fields(self, prompt_lower: str) -> list[str]:
        available = available_field_names() | {"first_name", "full_name"}
        known_prefixes = {field.split(".", 1)[0].split("_", 1)[0] for field in available}
        requested = set()
        for word in prompt_lower.replace("-", "_").split():
            candidate = word.strip(" ,.?")
            if "." in candidate or (
                "_" in candidate and candidate.split("_", 1)[0] in known_prefixes
            ):
                requested.add(candidate)
        return sorted(requested - available)

    def _recommended_tone(self) -> str:
        return "warm_assisted"

    def _requested_segments(self, prompt_lower: str) -> set[str]:
        segments = set()
        for value in ("premium", "preferred", "mass affluent", "mass"):
            if value in prompt_lower:
                segments.add(value)
        return segments

    def _requested_cities(self, prompt_lower: str) -> set[str]:
        cities = {customer["city"].lower() for customer in self.store.list_customers()}
        return {city for city in cities if city in prompt_lower}

    def _requested_employment(self, prompt_lower: str) -> set[str]:
        mapping = {
            "salaried": "salaried",
            "retired": "retired",
            "self employed professional": "self employed professional",
            "self-employed professional": "self employed professional",
            "self employed": "self employed",
            "self-employed": "self employed",
        }
        return {value for key, value in mapping.items() if key in prompt_lower}

    def _threshold_after(self, prompt_lower: str, labels: list[str]) -> int | None:
        for label in labels:
            position = prompt_lower.find(label)
            if position == -1:
                continue
            suffix = prompt_lower[position + len(label) :]
            match = NUMBER_PATTERN.search(suffix)
            if match:
                return self._parse_threshold(match.group())
        return None

    def _parse_threshold(self, value: str) -> int:
        normalized = value.strip().lower()
        number = float(re.search(r"\d+(?:\.\d+)?", normalized).group())
        if "crore" in normalized or normalized.endswith("cr"):
            return int(number * 10_000_000)
        if "lakh" in normalized or "lac" in normalized:
            return int(number * 100_000)
        return int(number)

    def _has_loan_intent(self, customer: dict[str, Any]) -> bool:
        activity = customer.get("digital_loan_activity", {})
        service = customer.get("service_interactions", {})
        credit = customer.get("credit_profile", {})
        # These are direct intent signals; sensitive liquidity triggers are not used for selection.
        return any(
            [
                activity.get("loan_application_status") == "Started_Not_Submitted",
                activity.get("emi_calculator_last_used_date"),
                activity.get("loan_product_page_sessions_30d", 0) >= 3,
                activity.get("loan_offer_clicked_date"),
                service.get("last_loan_related_inquiry_date"),
                credit.get("personal_loan_bureau_enquiry_date"),
            ]
        )

    def _extract_tone(self, prompt_lower: str) -> str | None:
        valid_tones = {
            style["tone_id"] for style in message_style_catalog(self.store.get_rules("messaging"))
        }
        normalized = prompt_lower.replace(" ", "_").replace("-", "_")
        for tone_id in valid_tones:
            if tone_id in normalized:
                return tone_id
        return None

    def _set_pending(self, state: SessionState, step: ApprovalStep) -> str:
        token = str(uuid.uuid4())[:8]
        state.pending_step = step
        state.approval_token = token
        logger.debug("Session %s pending approval step %s", state.session_id, step)
        return token

    def _clear_pending(self, state: SessionState) -> None:
        state.pending_step = None
        state.approval_token = None

    def _event(
        self,
        state: SessionState,
        event_type: str,
        message: str,
        payload: dict[str, Any],
    ) -> WorkflowEvent:
        logger.info(
            "Workflow event emitted",
            extra={
                "event_type": event_type,
                "session_id": state.session_id,
                "payload_keys": sorted(payload),
            },
        )
        return self.store.add_event(
            state.session_id,
            WorkflowEvent(event_type=event_type, message=message, payload=payload),
        )

    def _is_help(self, prompt_lower: str) -> bool:
        return prompt_lower in {"help", "what can you do", "show options", "capabilities"}

    def _is_field_catalog(self, prompt_lower: str) -> bool:
        return "field" in prompt_lower or "data" in prompt_lower

    def _is_check_catalog(self, prompt_lower: str) -> bool:
        return "check" in prompt_lower or "rule" in prompt_lower

    def _is_message_style_catalog(self, prompt_lower: str) -> bool:
        return "message style" in prompt_lower or "tone" in prompt_lower or "format" in prompt_lower

    def _extract_check_ids(self, prompt_lower: str) -> list[str]:
        all_ids = {
            check["rule_id"] for check in check_catalog(self.store.get_rules("shortlisting"))
        }
        extracted = [match.group().upper() for match in CHECK_ID_PATTERN.finditer(prompt_lower)]
        return [rule_id for rule_id in extracted if rule_id in all_ids]

    def _extract_customer_ids(self, prompt_lower: str) -> list[str]:
        seen: set[str] = set()
        customer_ids: list[str] = []
        for match in CUSTOMER_ID_PATTERN.finditer(prompt_lower):
            customer_id = match.group().upper()
            if customer_id not in seen:
                customer_ids.append(customer_id)
                seen.add(customer_id)
        return customer_ids

    def _has_approval_token(self, prompt_lower: str, token: str | None) -> bool:
        return token is not None and token.lower() in prompt_lower

    def _is_approval(self, prompt_lower: str, token: str | None) -> bool:
        return self._has_approval_token(prompt_lower, token)

    def strands_tools(self) -> list[Any]:
        from businessnext_agent.orchestration.agent_tools import build_workflow_tools

        return build_workflow_tools(self)

    def close(self) -> None:
        self.store.close()
