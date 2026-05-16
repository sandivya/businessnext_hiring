export type AgentStatus = "completed" | "needs_approval" | "needs_clarification" | "error";

export type WorkflowEvent = {
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
};

export type AgentResponse = {
  session_id: string;
  status: AgentStatus;
  message: string;
  suggested_prompts: string[];
  approval_token: string | null;
  events: WorkflowEvent[];
  structured_result: Record<string, unknown>;
};

export type AgenticRoute = {
  intent: string;
  tool_name: string;
  rationale: string;
  extracted_filters?: Record<string, unknown>;
  risk_flags?: string[];
};

export type TopCustomer = {
  customer_id: string;
  name: string;
  score: number;
  priority: string;
  likelihood_pct: number;
  recommended_channel?: string | null;
  offer_amount?: number | null;
  next_action?: string;
  reason_codes?: string[];
  passed_checks?: RuleOutcome[];
  failed_checks?: RuleOutcome[];
};

export type ExcludedCustomer = {
  customer_id: string;
  name: string;
  failed_hard_filters: string[];
  failed_checks?: RuleOutcome[];
};

export type CustomerDetailItem = {
  label: string;
  value: string;
  intentSignal?: string;
};

export type CustomerDetailGroup = {
  title: string;
  items: CustomerDetailItem[];
};

export type CustomerSummary = {
  customerId: string;
  fullName: string;
  age: number;
  city: string;
  state: string;
  segment: string;
  employmentType: string;
  monthlyIncome: number;
  totalRelationshipValue: number;
  bureauScore: number | null;
  internalRiskBand: string;
  preferredContactChannel: string;
  marketingConsent: boolean;
  dndFlag: boolean;
  highValue: boolean;
  contactable: boolean;
  loanIntentSignals: string[];
  detailGroups: CustomerDetailGroup[];
};

export type CustomerFilters = {
  search: string;
  segments: string[];
  cities: string[];
  employmentTypes: string[];
  loanIntentOnly: boolean;
  highValueOnly: boolean;
  contactableOnly: boolean;
};

export type CheckDefinition = {
  rule_id: string;
  name: string;
  type: "hard_filter" | "scoring";
  category?: string;
  points?: number;
  summary: string;
};

export type MessageStyle = {
  tone_id: string;
  display_name: string;
  best_for: string[];
  style: string;
  sample_opening: string;
};

export type CatalogResponse = {
  fields: Record<string, { field: string; description: string }[]>;
  checks: CheckDefinition[];
  styles: MessageStyle[];
};

export type CustomerEvaluation = {
  customer_id: string;
  full_name: string;
  eligible: boolean;
  score: number;
  priority_band: string;
  priority_label: string;
  heuristic_likelihood_pct: number;
  failed_hard_filters: RuleOutcome[];
  matched_rules: RuleOutcome[];
  missing_fields: string[];
  recommendation: {
    product: string;
    offer_type: string;
    suggested_action: string;
    preferred_channel?: string | null;
    amount?: number | null;
    rate_pct?: number | null;
    rationale: string[];
  };
};

export type RuleOutcome = {
  rule_id: string;
  display_name: string;
  passed: boolean;
  points: number;
  category?: string | null;
  reason: string;
};

export type MessageDraft = {
  customer_id: string;
  tone_id: string;
  template_id: string;
  channel: string;
  subject?: string | null;
  body: string;
  cta: string;
  safety_notes: string[];
  source_evidence: string[];
};
