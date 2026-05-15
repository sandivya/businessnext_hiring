import { describe, expect, it } from "vitest";

import { emptyFilters } from "@/lib/customers";
import {
  buildApprovalPrompt,
  buildCheckApprovalPrompt,
  buildFilteredCohortPrompt,
  buildSelectedCustomersPrompt,
  buildToneApprovalPrompt
} from "@/lib/prompts";

describe("agent prompt builders", () => {
  it("builds explicit customer prompts", () => {
    expect(buildSelectedCustomersPrompt(["CUST0001", "CUST0002"], "Rank fast")).toContain(
      "CUST0001 CUST0002"
    );
    expect(() => buildSelectedCustomersPrompt([], "")).toThrow("Select at least one");
  });

  it("builds filter prompts in agent-readable language", () => {
    const prompt = buildFilteredCohortPrompt(
      {
        ...emptyFilters,
        highValueOnly: true,
        segments: ["Premium"],
        cities: ["Mumbai"],
        employmentTypes: ["Salaried"],
        loanIntentOnly: true
      },
      "Focus on this month"
    );

    expect(prompt).toContain("high-value premium salaried customers in Mumbai");
    expect(prompt).toContain("likely to convert");
  });

  it("builds approval prompts", () => {
    expect(buildApprovalPrompt("abc123")).toBe("approve abc123");
    expect(buildCheckApprovalPrompt("abc123", ["INT001"])).toBe("approve abc123 INT001");
    expect(buildToneApprovalPrompt("abc123", "premium_exclusive")).toBe(
      "approve abc123 premium_exclusive"
    );
  });
});
