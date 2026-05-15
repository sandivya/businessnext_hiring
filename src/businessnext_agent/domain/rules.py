"""Deterministic shortlisting, scoring, and recommendation logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from businessnext_agent.schemas import CustomerEvaluation, Recommendation, RuleOutcome

logger = logging.getLogger(__name__)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _get_path(data: dict[str, Any], path: str) -> tuple[Any, list[str]]:
    if path.endswith(".length"):
        value, missing = _get_path(data, path.removesuffix(".length"))
        return (
            (len(value), [])
            if missing == [] and isinstance(value, list)
            else (None, missing or [path])
        )
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None, [path]
    return current, []


def _resolve_expression(data: dict[str, Any], expression: str) -> tuple[Any, list[str]]:
    if " - " in expression:
        left_path, right_path = expression.split(" - ", 1)
        left, left_missing = _get_path(data, left_path)
        right, right_missing = _get_path(data, right_path)
        if left_missing or right_missing:
            return None, left_missing + right_missing
        if left is None or right is None:
            return None, []
        return left - right, []
    if " / " in expression:
        left_path, right_path = expression.split(" / ", 1)
        left, left_missing = _get_path(data, left_path)
        right, right_missing = _get_path(data, right_path)
        if left_missing or right_missing:
            return None, left_missing + right_missing
        if left is None or right in (0, None):
            return None, left_missing + right_missing
        return left / right, []
    return _get_path(data, expression)


@dataclass(frozen=True)
class ConditionResult:
    passed: bool
    missing_fields: list[str] = field(default_factory=list)


class ConditionEvaluator:
    """Evaluate the condition mini-language from the supplied rules JSON."""

    def __init__(self, as_of_date: date) -> None:
        self.as_of_date = as_of_date

    def evaluate(self, condition: dict[str, Any], customer: dict[str, Any]) -> ConditionResult:
        if "all" in condition:
            results = [self.evaluate(item, customer) for item in condition["all"]]
            return ConditionResult(
                all(item.passed for item in results),
                [field for item in results for field in item.missing_fields],
            )
        if "any" in condition:
            results = [self.evaluate(item, customer) for item in condition["any"]]
            missing = (
                []
                if any(item.passed for item in results)
                else [field for item in results for field in item.missing_fields]
            )
            return ConditionResult(any(item.passed for item in results), missing)
        value, missing = _resolve_expression(customer, condition["field"])
        if missing:
            return ConditionResult(False, missing)
        expected = condition.get("value")
        operator = condition["operator"]
        return ConditionResult(self._compare(value, operator, expected))

    def _compare(self, value: Any, operator: str, expected: Any) -> bool:
        if operator == "equals":
            return value == expected
        if value is None and operator in {"greater_than", "greater_than_or_equal_to", "in"}:
            return False
        if operator == "greater_than":
            return value > expected
        if operator == "greater_than_or_equal_to":
            return value >= expected
        if operator == "in":
            return value in expected
        if operator == "is_null":
            return value is None
        if operator == "not_null":
            return value is not None
        if operator == "within_last_days":
            value_date = _parse_date(value)
            return value_date is not None and 0 <= (self.as_of_date - value_date).days <= expected
        if operator == "older_than_days":
            value_date = _parse_date(value)
            return value_date is not None and (self.as_of_date - value_date).days > expected
        msg = f"Unsupported operator: {operator}"
        raise ValueError(msg)


class ScoringEngine:
    """Apply hard filters first, then capped weighted scoring."""

    def __init__(
        self,
        shortlisting_rules: dict[str, Any],
        as_of_date: date,
        enabled_rule_ids: set[str] | None = None,
    ) -> None:
        self.shortlisting_rules = shortlisting_rules
        self.evaluator = ConditionEvaluator(as_of_date)
        self.enabled_rule_ids = enabled_rule_ids
        self.hard_filters = self._section("hard_filters")["rules"]
        scoring = self._section("weighted_scoring")
        self.categories = scoring["categories"]
        self.bands = self._section("shortlist_bands")["bands"]

    def evaluate_customer(self, customer: dict[str, Any]) -> CustomerEvaluation:
        logger.debug("Evaluating customer %s", customer.get("customer_id"))
        failed_filters: list[RuleOutcome] = []
        missing_fields: set[str] = set()
        for rule in self.hard_filters:
            result = self.evaluator.evaluate(rule["technical_condition"], customer)
            missing_fields.update(result.missing_fields)
            if not result.passed:
                failed_filters.append(
                    RuleOutcome(
                        rule_id=rule["rule_id"],
                        display_name=rule["display_name"],
                        passed=False,
                        reason=rule["condition_summary"],
                    )
                )
        if failed_filters:
            logger.info(
                "Customer %s excluded by %s hard filters",
                customer.get("customer_id"),
                len(failed_filters),
            )
            return self._excluded_evaluation(customer, failed_filters, sorted(missing_fields))
        score = 0
        matched_rules: list[RuleOutcome] = []
        for category in self.categories:
            category_points = 0
            for rule in category["rules"]:
                # The selected-check list only narrows optional scoring rules.
                # Mandatory hard filters have already run above for every customer.
                if (
                    self.enabled_rule_ids is not None
                    and rule["rule_id"] not in self.enabled_rule_ids
                ):
                    continue
                result = self.evaluator.evaluate(rule["technical_condition"], customer)
                missing_fields.update(result.missing_fields)
                if result.passed:
                    category_points += int(rule["points"])
                    matched_rules.append(
                        RuleOutcome(
                            rule_id=rule["rule_id"],
                            display_name=rule["display_name"],
                            passed=True,
                            points=int(rule["points"]),
                            category=category["category_id"],
                            reason=rule["condition_summary"],
                        )
                    )
            score += min(category_points, int(category["category_weight"]))
        band = self._band_for_score(score)
        return CustomerEvaluation(
            customer_id=customer["customer_id"],
            full_name=customer["full_name"],
            eligible=True,
            score=score,
            priority_band=band["band_id"],
            priority_label=band["display_name"],
            heuristic_likelihood_pct=self._likelihood(score),
            matched_rules=matched_rules,
            missing_fields=sorted(missing_fields),
            recommendation=self._recommend(customer, band, matched_rules),
        )

    def rank(self, customers: list[dict[str, Any]], limit: int = 10) -> list[CustomerEvaluation]:
        evaluations = [self.evaluate_customer(customer) for customer in customers]
        return sorted(
            evaluations,
            key=lambda item: (
                item.eligible,
                item.score,
                item.heuristic_likelihood_pct,
                item.recommendation.amount or 0,
            ),
            reverse=True,
        )[:limit]

    def _section(self, section_id: str) -> dict[str, Any]:
        return next(
            section
            for section in self.shortlisting_rules["ui_sections"]
            if section["section_id"] == section_id
        )

    def _excluded_evaluation(
        self,
        customer: dict[str, Any],
        failed_filters: list[RuleOutcome],
        missing_fields: list[str],
    ) -> CustomerEvaluation:
        return CustomerEvaluation(
            customer_id=customer["customer_id"],
            full_name=customer["full_name"],
            eligible=False,
            score=0,
            priority_band="EXCLUDED",
            priority_label="Excluded by hard filters",
            heuristic_likelihood_pct=0,
            failed_hard_filters=failed_filters,
            missing_fields=missing_fields,
            recommendation=Recommendation(
                offer_type="Not recommended",
                suggested_action="Do not contact for this campaign.",
                preferred_channel=customer.get("preferred_contact_channel"),
                rationale=[rule.display_name for rule in failed_filters],
            ),
        )

    def _band_for_score(self, score: int) -> dict[str, Any]:
        return next(
            band for band in self.bands if int(band["score_min"]) <= score <= int(band["score_max"])
        )

    def _likelihood(self, score: int) -> int:
        if score >= 80:
            return min(95, 75 + (score - 80))
        if score >= 65:
            return 55 + round((score - 65) * (19 / 14))
        if score >= 50:
            return 30 + round((score - 50) * (24 / 14))
        return max(5, round(score * 0.6))

    def _recommend(
        self,
        customer: dict[str, Any],
        band: dict[str, Any],
        matched_rules: list[RuleOutcome],
    ) -> Recommendation:
        loan_profile = customer.get("loan_profile", {})
        amount = loan_profile.get("pre_approved_personal_loan_amount") or None
        rate = loan_profile.get("pre_approved_personal_loan_rate_pct") or None
        strongest = [rule.display_name for rule in matched_rules[:4]]
        return Recommendation(
            offer_type="Pre-approved personal loan" if amount else "Personal loan exploration",
            suggested_action=band["suggested_action"],
            preferred_channel=customer.get("preferred_contact_channel"),
            amount=amount,
            rate_pct=rate,
            rationale=strongest,
        )
