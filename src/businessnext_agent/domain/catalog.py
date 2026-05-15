"""User-facing catalogs for non-technical discovery."""

from __future__ import annotations

from typing import Any

FIELD_CATALOG: dict[str, list[tuple[str, str]]] = {
    "Customer profile": [
        ("full_name", "Customer name"),
        ("age", "Age"),
        ("city", "City"),
        ("customer_segment", "Customer value segment"),
        ("employment_type", "Employment type"),
    ],
    "Banking relationship": [
        ("bank_tenure_months", "Months with the bank"),
        ("products_held", "Products already held"),
        ("total_relationship_value", "Total relationship value"),
        ("avg_monthly_balance_6m", "Average balance over six months"),
    ],
    "Credit and risk": [
        ("credit_profile.bureau_score", "Credit bureau score"),
        ("credit_profile.internal_risk_band", "Internal risk band"),
        ("credit_profile.missed_emi_count_24m", "Missed EMI count in 24 months"),
        ("credit_profile.delinquency_last_12m", "Recent delinquency flag"),
    ],
    "Loan intent": [
        ("digital_loan_activity.loan_application_status", "Loan application status"),
        ("digital_loan_activity.emi_calculator_last_used_date", "Recent EMI calculator use"),
        ("digital_loan_activity.loan_product_page_sessions_30d", "Loan page visits"),
        ("service_interactions.last_loan_related_inquiry_date", "Recent loan inquiry"),
    ],
    "Contactability": [
        ("marketing_consent", "Marketing consent"),
        ("dnd_flag", "Do-not-disturb flag"),
        ("preferred_contact_channel", "Preferred contact channel"),
        ("app_last_active_date", "Last mobile app activity"),
    ],
    "Recent financial activity": [
        ("recent_financial_activity.fd_closed_last_60d", "Recent fixed deposit closure"),
        ("recent_financial_activity.mf_redeemed_last_60d", "Recent mutual fund redemption"),
        ("recent_financial_activity.large_single_debit_amount_30d", "Large recent debit"),
        (
            "recent_financial_activity.balance_near_zero_before_salary_count_3m",
            "Near-zero balance before salary count",
        ),
    ],
}


EXAMPLE_PROMPTS = [
    "Find high-value customers likely to convert for a personal loan this month.",
    "Show me all available customer fields.",
    "Which checks can you run before shortlisting customers?",
    "Rank premium customers by personal-loan conversion likelihood.",
    "Show the message styles available for outreach.",
]


def capability_message() -> str:
    """Return the non-technical help card shown at the start of a session."""

    return (
        "I can help you run a personal-loan outreach workflow end to end.\n\n"
        "What I can do:\n"
        "1. Explain available customer fields in plain language.\n"
        "2. Select customers from your data using natural-language criteria.\n"
        "3. Run eligibility checks, scoring, and conversion-likelihood estimates.\n"
        "4. Recommend the next personal-loan outreach action.\n"
        "5. Show message styles and draft personalized messages after your approval.\n\n"
        "I will ask for approval before each major step so you stay in control."
    )


def field_catalog() -> dict[str, list[dict[str, str]]]:
    """Return a frontend-friendly field catalog."""

    return {
        group: [{"field": field, "description": description} for field, description in fields]
        for group, fields in FIELD_CATALOG.items()
    }


def check_catalog(shortlisting_rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten hard filters and weighted checks into one readable catalog."""

    catalog: list[dict[str, Any]] = []
    for section in shortlisting_rules["ui_sections"]:
        if section["section_id"] == "hard_filters":
            catalog.extend(
                {
                    "rule_id": rule["rule_id"],
                    "name": rule["display_name"],
                    "type": "hard_filter",
                    "summary": rule["condition_summary"],
                }
                for rule in section["rules"]
            )
        if section["section_id"] == "weighted_scoring":
            for category in section["categories"]:
                catalog.extend(
                    {
                        "rule_id": rule["rule_id"],
                        "name": rule["display_name"],
                        "type": "scoring",
                        "category": category["category_title"],
                        "points": rule["points"],
                        "summary": rule["condition_summary"],
                    }
                    for rule in category["rules"]
                )
    return catalog


def message_style_catalog(messaging_rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Return available tone/style choices."""

    return [
        {
            "tone_id": tone["tone_id"],
            "display_name": tone["display_name"],
            "best_for": tone["best_for"],
            "style": tone["style"],
            "sample_opening": tone["sample_opening"],
        }
        for tone in messaging_rules["tone_selection_rules"]
    ]


def available_field_names() -> set[str]:
    """Return all top-level catalog field identifiers."""

    return {field for fields in FIELD_CATALOG.values() for field, _ in fields}
