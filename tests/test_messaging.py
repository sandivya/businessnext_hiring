from __future__ import annotations

from dataclasses import dataclass

from businessnext_agent.domain.messaging import (
    FakeMessageModel,
    MessagingPolicy,
    StrandsBedrockMessageModel,
    _format_amount,
)
from businessnext_agent.domain.rules import ScoringEngine
from businessnext_agent.schemas import CustomerEvaluation, Recommendation


@dataclass
class FakeResult:
    message: str


@dataclass
class FakeStructuredResult:
    structured_output: object


class FakeAgent:
    def __call__(self, prompt: str, structured_output_model=None):
        return FakeStructuredResult(
            structured_output=structured_output_model(body=f"drafted: {prompt[:4]}")
        )


class FailingAgent:
    def __call__(self, prompt: str, structured_output_model=None):
        raise RuntimeError("temporary model failure")


def test_messaging_policy_and_redaction(service) -> None:
    customers = service.store.list_customers()
    engine = ScoringEngine(
        service.store.get_rules("shortlisting"), __import__("datetime").date(2026, 5, 15)
    )
    evaluations = engine.rank(customers, limit=5)
    policy = MessagingPolicy(service.store.get_rules("messaging"), FakeMessageModel())
    drafts = policy.draft_messages(
        evaluations,
        {customer["customer_id"]: customer for customer in customers},
        "warm_assisted",
    )
    assert drafts
    assert drafts[0].body
    assert drafts[0].tone_id
    assert "Sensitive inferred triggers" in drafts[0].safety_notes[0]
    assert "low balance" not in policy._redact("Your low balance was noticed").lower()


def test_strands_bedrock_message_model_uses_injected_agent() -> None:
    def factory():
        return FakeAgent()

    model = StrandsBedrockMessageModel(factory)
    assert model.draft("hello world", "fallback") == "drafted: hell"


def test_strands_bedrock_message_model_fallbacks() -> None:
    def failing_factory():
        return FailingAgent()

    message_model = StrandsBedrockMessageModel(failing_factory)
    assert message_model.draft("hello", "fallback") == "fallback"

    class DictAgent:
        def __call__(self, prompt: str, structured_output_model=None):
            return FakeResult(message={"content": "dict body"})

    def dict_factory():
        return DictAgent()

    assert StrandsBedrockMessageModel(dict_factory).draft("hello", "fallback") == "dict body"

    class ListAgent:
        def __call__(self, prompt: str, structured_output_model=None):
            return FakeResult(message=["list", "body"])

    def list_factory():
        return ListAgent()

    assert StrandsBedrockMessageModel(list_factory).draft("hello", "fallback") == "list body"

    class RawAgent:
        def __call__(self, prompt: str, structured_output_model=None):
            return "raw body"

    def raw_factory():
        return RawAgent()

    assert StrandsBedrockMessageModel(raw_factory).draft("hello", "fallback") == "raw body"


def test_message_scenario_fallbacks_and_safety_note(service) -> None:
    policy = MessagingPolicy(service.store.get_rules("messaging"), FakeMessageModel())
    customer = {
        "customer_id": "C1",
        "full_name": "Asha Rao",
        "customer_segment": "Premium",
        "digital_loan_activity": {},
        "service_interactions": {},
        "loan_profile": {"existing_loan_closure_months_remaining": 2},
        "recent_financial_activity": {},
    }
    evaluation = CustomerEvaluation(
        customer_id="C1",
        full_name="Asha Rao",
        eligible=True,
        score=81,
        priority_band="P1",
        priority_label="Priority 1",
        heuristic_likelihood_pct=76,
        recommendation=Recommendation(
            offer_type="Personal loan exploration",
            suggested_action="Call",
            amount=None,
        ),
    )
    assert _format_amount(None) == "your available amount"
    assert policy._scenario(customer, evaluation) == "existing_loan_near_closure"
    template = policy._select_template(customer, evaluation, "does_not_exist")
    assert template["scenario"] == "existing_loan_near_closure"

    customer["loan_profile"] = {"existing_loan_closure_months_remaining": 8}
    customer["recent_financial_activity"] = {"fd_closed_last_60d": True}
    assert policy._scenario(customer, evaluation) == "fd_or_mf_liquidity_context"
    drafts = policy.draft_messages([evaluation], {"C1": customer}, "formal_rm")
    assert len(drafts[0].safety_notes) == 2

    customer["recent_financial_activity"] = {}
    assert policy._scenario(customer, evaluation) == "salary_day_offer"

    amount_eval = evaluation.model_copy(
        update={
            "recommendation": Recommendation(
                offer_type="Pre-approved personal loan",
                suggested_action="Email",
                amount=500000,
            )
        }
    )
    assert policy._scenario(customer, amount_eval) == "pre_approved_high_value"
