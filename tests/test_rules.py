from __future__ import annotations

from datetime import date

import pytest

from businessnext_agent.domain.rules import ConditionEvaluator, ScoringEngine


def test_condition_evaluator_operators() -> None:
    customer = {
        "flag": True,
        "score": 10,
        "segment": "Premium",
        "items": [1, 2, 3],
        "last_seen": "2026-05-14",
        "old_seen": "2026-04-01",
        "left": 10,
        "right": 5,
        "zero": 0,
        "empty": None,
    }
    evaluator = ConditionEvaluator(date(2026, 5, 15))
    assert evaluator.evaluate(
        {"field": "flag", "operator": "equals", "value": True}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "score", "operator": "greater_than", "value": 9}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "score", "operator": "greater_than_or_equal_to", "value": 10}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "segment", "operator": "in", "value": ["Premium"]}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "empty", "operator": "is_null", "value": True}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "flag", "operator": "not_null", "value": True}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "last_seen", "operator": "within_last_days", "value": 3}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "old_seen", "operator": "older_than_days", "value": 30}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "last_seen", "operator": "within_last_days", "value": 3},
        {**customer, "last_seen": date(2026, 5, 14)},
    ).passed
    assert evaluator.evaluate(
        {"field": "items.length", "operator": "equals", "value": 3}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "left - right", "operator": "equals", "value": 5}, customer
    ).passed
    assert evaluator.evaluate(
        {"field": "left / right", "operator": "equals", "value": 2}, customer
    ).passed
    assert not evaluator.evaluate(
        {"field": "left - missing", "operator": "equals", "value": 1}, customer
    ).passed
    assert not evaluator.evaluate(
        {"field": "left / missing", "operator": "equals", "value": 1}, customer
    ).passed
    assert not evaluator.evaluate(
        {"field": "left / zero", "operator": "equals", "value": 1}, customer
    ).passed
    assert not evaluator.evaluate(
        {"field": "items.length", "operator": "equals", "value": 1}, {"items": "bad"}
    ).passed
    assert not evaluator.evaluate(
        {"field": "missing", "operator": "equals", "value": 1}, customer
    ).passed
    assert evaluator.evaluate(
        {
            "all": [
                {"field": "flag", "operator": "equals", "value": True},
                {"field": "score", "operator": "greater_than", "value": 1},
            ]
        },
        customer,
    ).passed
    assert evaluator.evaluate(
        {
            "any": [
                {"field": "missing", "operator": "equals", "value": 1},
                {"field": "flag", "operator": "equals", "value": True},
            ]
        },
        customer,
    ).passed
    with pytest.raises(ValueError, match="Unsupported operator"):
        evaluator.evaluate({"field": "flag", "operator": "unknown", "value": True}, customer)


def test_scoring_engine_rank_and_exclusion(service) -> None:
    metadata = service.store.get_metadata("customers")
    engine = ScoringEngine(
        service.store.get_rules("shortlisting"), date.fromisoformat(metadata["generated_on"])
    )
    ranked = engine.rank(service.store.list_customers(), limit=5)
    assert len(ranked) == 5
    assert ranked[0].eligible is True
    assert 0 <= ranked[0].score <= 100
    assert ranked[0].priority_band in {"P1", "P2", "P3", "P4"}
    assert ranked[0].recommendation.product == "personal_loan"
    assert engine._likelihood(80) == 75

    customer = service.store.list_customers()[0].copy()
    customer["marketing_consent"] = False
    excluded = engine.evaluate_customer(customer)
    assert excluded.eligible is False
    assert excluded.priority_band == "EXCLUDED"
    assert excluded.failed_hard_filters[0].rule_id == "HF001"

    limited = ScoringEngine(
        service.store.get_rules("shortlisting"),
        date.fromisoformat(metadata["generated_on"]),
        {"INT001"},
    ).rank(service.store.list_customers(), limit=5)
    assert all(
        rule.rule_id == "INT001"
        for item in limited
        for rule in item.matched_rules
        if rule.category == "intent_signals"
    )
