import type { CustomerFilters } from "@/lib/types";

export function buildSelectedCustomersPrompt(customerIds: string[], objective: string): string {
  if (customerIds.length === 0) {
    throw new Error("Select at least one customer before running the agent.");
  }
  return [
    `Evaluate selected customers ${customerIds.join(" ")} for personal loan outreach.`,
    objective.trim() ? `Objective: ${objective.trim()}.` : "Rank them by conversion likelihood."
  ].join(" ");
}

export function buildFilteredCohortPrompt(filters: CustomerFilters, objective: string): string {
  const parts = ["Find"];
  if (filters.highValueOnly) {
    parts.push("high-value");
  }
  if (filters.segments.length > 0) {
    parts.push(filters.segments.join(" and ").toLowerCase());
  }
  if (filters.employmentTypes.length > 0) {
    parts.push(filters.employmentTypes.join(" and ").toLowerCase());
  }
  parts.push("customers");
  if (filters.cities.length > 0) {
    parts.push(`in ${filters.cities.join(" or ")}`);
  }
  if (filters.loanIntentOnly) {
    parts.push("likely to convert for a personal loan this month");
  } else {
    parts.push("for personal loan shortlisting");
  }
  if (objective.trim()) {
    parts.push(`Objective: ${objective.trim()}.`);
  }
  return parts.join(" ");
}

export function buildApprovalPrompt(token: string, additions: string[] = []): string {
  return ["approve", token, ...additions].filter(Boolean).join(" ");
}

export function buildCheckApprovalPrompt(token: string, checkIds: string[]): string {
  return buildApprovalPrompt(token, checkIds);
}

export function buildToneApprovalPrompt(token: string, toneId: string): string {
  return buildApprovalPrompt(token, [toneId]);
}
