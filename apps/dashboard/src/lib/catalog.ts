import type { CatalogResponse, CheckDefinition, MessageStyle } from "@/lib/types";

type ShortlistingRules = {
  ui_sections: Array<Record<string, any>>;
};

type MessagingRules = {
  tone_selection_rules: MessageStyle[];
};

export const fieldCatalog: CatalogResponse["fields"] = {
  "Customer profile": [
    { field: "full_name", description: "Customer name" },
    { field: "age", description: "Age" },
    { field: "city", description: "City" },
    { field: "customer_segment", description: "Customer value segment" },
    { field: "employment_type", description: "Employment type" }
  ],
  "Banking relationship": [
    { field: "bank_tenure_months", description: "Months with the bank" },
    { field: "products_held", description: "Products already held" },
    { field: "total_relationship_value", description: "Total relationship value" },
    { field: "avg_monthly_balance_6m", description: "Average balance over six months" }
  ],
  "Credit and risk": [
    { field: "credit_profile.bureau_score", description: "Credit bureau score" },
    { field: "credit_profile.internal_risk_band", description: "Internal risk band" },
    { field: "credit_profile.missed_emi_count_24m", description: "Missed EMI count" },
    { field: "credit_profile.delinquency_last_12m", description: "Recent delinquency flag" }
  ],
  "Loan intent": [
    {
      field: "digital_loan_activity.loan_application_status",
      description: "Loan application status"
    },
    {
      field: "digital_loan_activity.emi_calculator_last_used_date",
      description: "Recent EMI calculator use"
    },
    {
      field: "digital_loan_activity.loan_product_page_sessions_30d",
      description: "Loan page visits"
    },
    {
      field: "service_interactions.last_loan_related_inquiry_date",
      description: "Recent loan inquiry"
    }
  ],
  Contactability: [
    { field: "marketing_consent", description: "Marketing consent" },
    { field: "dnd_flag", description: "Do-not-disturb flag" },
    { field: "preferred_contact_channel", description: "Preferred contact channel" },
    { field: "app_last_active_date", description: "Last mobile app activity" }
  ],
  "Recent financial activity": [
    { field: "recent_financial_activity.fd_closed_last_60d", description: "Recent FD closure" },
    {
      field: "recent_financial_activity.mf_redeemed_last_60d",
      description: "Recent mutual fund redemption"
    },
    {
      field: "recent_financial_activity.large_single_debit_amount_30d",
      description: "Large recent debit"
    },
    {
      field: "recent_financial_activity.balance_near_zero_before_salary_count_3m",
      description: "Near-zero balance before salary count"
    }
  ]
};

export function mapChecks(shortlistingRules: ShortlistingRules): CheckDefinition[] {
  const catalog: CheckDefinition[] = [];
  for (const section of shortlistingRules.ui_sections) {
    if (section.section_id === "hard_filters") {
      for (const rule of section.rules ?? []) {
        catalog.push({
          rule_id: rule.rule_id,
          name: rule.display_name,
          type: "hard_filter",
          summary: rule.condition_summary
        });
      }
    }
    if (section.section_id === "weighted_scoring") {
      for (const category of section.categories ?? []) {
        for (const rule of category.rules ?? []) {
          catalog.push({
            rule_id: rule.rule_id,
            name: rule.display_name,
            type: "scoring",
            category: category.category_title,
            points: rule.points,
            summary: rule.condition_summary
          });
        }
      }
    }
  }
  return catalog;
}

export function mapMessageStyles(messagingRules: MessagingRules): MessageStyle[] {
  return messagingRules.tone_selection_rules.map((tone) => ({
    tone_id: tone.tone_id,
    display_name: tone.display_name,
    best_for: tone.best_for,
    style: tone.style,
    sample_opening: tone.sample_opening
  }));
}
