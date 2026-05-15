import { describe, expect, it } from "vitest";

import { emptyFilters, filterCustomers, mapCustomerSummary } from "@/lib/customers";

const rawCustomer = {
  customer_id: "CUST0001",
  full_name: "Aarav Verma",
  age: 36,
  city: "Nagpur",
  state: "Maharashtra",
  customer_segment: "Premium",
  employment_type: "Salaried",
  employer_category: "SME",
  monthly_income: 105000,
  preferred_contact_channel: "Push Notification",
  marketing_consent: true,
  dnd_flag: false,
  bank_tenure_months: 169,
  products_held: ["Savings Account", "Fixed Deposit"],
  total_relationship_value: 3205000,
  avg_monthly_balance_6m: 229504,
  credit_profile: {
    bureau_score: 778,
    internal_risk_band: "Low",
    missed_emi_count_24m: 0,
    personal_loan_bureau_enquiry_date: "2026-05-01"
  },
  loan_profile: {
    pre_approved_personal_loan_amount: 650000,
    pre_approved_personal_loan_rate_pct: 11.2
  },
  digital_loan_activity: {
    loan_application_status: "Started_Not_Submitted",
    emi_calculator_last_used_date: "2026-05-10",
    loan_product_page_sessions_30d: 4
  },
  service_interactions: {
    last_loan_related_inquiry_date: null
  },
  recent_financial_activity: {
    large_single_debit_amount_30d: 0,
    fd_closed_last_60d: false,
    mf_redeemed_last_60d: false,
    salary_increase_pct_last_2m: 4
  }
};

describe("customer mapping", () => {
  it("creates a safe customer summary with intent signals", () => {
    const summary = mapCustomerSummary(rawCustomer);

    expect(summary.customerId).toBe("CUST0001");
    expect(summary.highValue).toBe(true);
    expect(summary.contactable).toBe(true);
    expect(summary.loanIntentSignals).toContain("Incomplete application");
    expect(summary.detailGroups).toHaveLength(5);
  });

  it("filters by segment, search, and intent", () => {
    const customer = mapCustomerSummary(rawCustomer);
    const filtered = filterCustomers([customer], {
      ...emptyFilters,
      search: "aarav",
      segments: ["Premium"],
      loanIntentOnly: true
    });

    expect(filtered).toEqual([customer]);
    expect(filterCustomers([customer], { ...emptyFilters, cities: ["Mumbai"] })).toEqual([]);
  });
});
