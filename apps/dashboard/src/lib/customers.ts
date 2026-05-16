import type { CustomerFilters, CustomerSummary } from "@/lib/types";

type RawCustomer = Record<string, any>;

const HIGH_VALUE_THRESHOLD = 300000;

export const emptyFilters: CustomerFilters = {
  search: "",
  segments: [],
  cities: [],
  employmentTypes: [],
  loanIntentOnly: false,
  highValueOnly: false,
  contactableOnly: false
};

export function mapCustomerSummary(customer: RawCustomer): CustomerSummary {
  const credit = customer.credit_profile ?? {};
  const activity = customer.digital_loan_activity ?? {};
  const service = customer.service_interactions ?? {};
  const recent = customer.recent_financial_activity ?? {};
  const loanProfile = customer.loan_profile ?? {};
  const loanIntentSignals = loanIntentLabels(customer);

  return {
    customerId: String(customer.customer_id),
    fullName: String(customer.full_name),
    age: Number(customer.age),
    city: String(customer.city),
    state: String(customer.state),
    segment: String(customer.customer_segment),
    employmentType: String(customer.employment_type),
    monthlyIncome: Number(customer.monthly_income ?? 0),
    totalRelationshipValue: Number(customer.total_relationship_value ?? 0),
    bureauScore: credit.bureau_score ?? null,
    internalRiskBand: String(credit.internal_risk_band ?? "-"),
    preferredContactChannel: String(customer.preferred_contact_channel ?? "-"),
    marketingConsent: Boolean(customer.marketing_consent),
    dndFlag: Boolean(customer.dnd_flag),
    highValue: Number(customer.total_relationship_value ?? 0) >= HIGH_VALUE_THRESHOLD,
    contactable: Boolean(customer.marketing_consent) && !Boolean(customer.dnd_flag),
    loanIntentSignals,
    detailGroups: [
      {
        title: "Profile",
        items: [
          detail("Customer ID", customer.customer_id),
          detail("Age", customer.age),
          detail("Segment", customer.customer_segment),
          detail("Employment", customer.employment_type),
          detail("Employer category", customer.employer_category)
        ]
      },
      {
        title: "Relationship",
        items: [
          detail("Bank tenure", `${customer.bank_tenure_months} months`),
          detail("Products held", (customer.products_held ?? []).join(", ")),
          detail("Total relationship value", customer.total_relationship_value),
          detail("Average monthly balance", customer.avg_monthly_balance_6m)
        ]
      },
      {
        title: "Credit And Loan",
        items: [
          detail("Bureau score", credit.bureau_score),
          detail("Risk band", credit.internal_risk_band),
          detail("Missed EMI count", credit.missed_emi_count_24m),
          detail("Pre-approved amount", loanProfile.pre_approved_personal_loan_amount),
          detail("Pre-approved rate", loanProfile.pre_approved_personal_loan_rate_pct)
        ]
      },
      {
        title: "Intent And Contact",
        items: [
          detail(
            "Application status",
            activity.loan_application_status,
            activity.loan_application_status === "Started_Not_Submitted"
              ? "Incomplete application"
              : undefined
          ),
          detail(
            "EMI calculator",
            activity.emi_calculator_last_used_date,
            activity.emi_calculator_last_used_date ? "EMI planning" : undefined
          ),
          detail(
            "Loan page visits",
            activity.loan_product_page_sessions_30d,
            Number(activity.loan_product_page_sessions_30d ?? 0) >= 3
              ? "Loan page visits"
              : undefined
          ),
          detail(
            "Offer clicked",
            activity.loan_offer_clicked_date,
            activity.loan_offer_clicked_date ? "Offer clicked" : undefined
          ),
          detail(
            "Loan inquiry",
            service.last_loan_related_inquiry_date,
            service.last_loan_related_inquiry_date ? "Loan inquiry" : undefined
          ),
          detail(
            "Bureau enquiry",
            credit.personal_loan_bureau_enquiry_date,
            credit.personal_loan_bureau_enquiry_date ? "Bureau enquiry" : undefined
          ),
          detail("Preferred channel", customer.preferred_contact_channel)
        ]
      },
      {
        title: "Recent Signals",
        items: [
          detail("Large debit", recent.large_single_debit_amount_30d),
          detail("FD closed", recent.fd_closed_last_60d),
          detail("MF redeemed", recent.mf_redeemed_last_60d),
          detail("Salary increase", recent.salary_increase_pct_last_2m)
        ]
      }
    ]
  };
}

export function filterCustomers(
  customers: CustomerSummary[],
  filters: CustomerFilters
): CustomerSummary[] {
  const search = filters.search.trim().toLowerCase();
  return customers.filter((customer) => {
    if (
      search &&
      ![
        customer.customerId,
        customer.fullName,
        customer.city,
        customer.segment,
        customer.employmentType
      ]
        .join(" ")
        .toLowerCase()
        .includes(search)
    ) {
      return false;
    }
    if (filters.segments.length > 0 && !filters.segments.includes(customer.segment)) {
      return false;
    }
    if (filters.cities.length > 0 && !filters.cities.includes(customer.city)) {
      return false;
    }
    if (
      filters.employmentTypes.length > 0 &&
      !filters.employmentTypes.includes(customer.employmentType)
    ) {
      return false;
    }
    if (filters.loanIntentOnly && customer.loanIntentSignals.length === 0) {
      return false;
    }
    if (filters.highValueOnly && !customer.highValue) {
      return false;
    }
    if (filters.contactableOnly && !customer.contactable) {
      return false;
    }
    return true;
  });
}

function loanIntentLabels(customer: RawCustomer): string[] {
  const activity = customer.digital_loan_activity ?? {};
  const service = customer.service_interactions ?? {};
  const credit = customer.credit_profile ?? {};
  const labels: string[] = [];
  if (activity.loan_application_status === "Started_Not_Submitted") {
    labels.push("Incomplete application");
  }
  if (activity.emi_calculator_last_used_date) {
    labels.push("EMI planning");
  }
  if (Number(activity.loan_product_page_sessions_30d ?? 0) >= 3) {
    labels.push("Loan page visits");
  }
  if (activity.loan_offer_clicked_date) {
    labels.push("Offer clicked");
  }
  if (service.last_loan_related_inquiry_date) {
    labels.push("Loan inquiry");
  }
  if (credit.personal_loan_bureau_enquiry_date) {
    labels.push("Bureau enquiry");
  }
  return labels;
}

function detail(label: string, value: unknown, intentSignal?: string) {
  return {
    label,
    value:
      value === null || value === undefined || value === ""
        ? "-"
        : Array.isArray(value)
          ? value.join(", ")
          : String(value),
    intentSignal
  };
}
