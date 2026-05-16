import { describe, expect, it } from "vitest";

import { mapChecks, mapMessageStyles } from "@/lib/catalog";

describe("catalog mapping", () => {
  it("flattens hard filters and scoring checks", () => {
    const checks = mapChecks({
      ui_sections: [
        {
          section_id: "hard_filters",
          rules: [{ rule_id: "HF001", display_name: "Consent", condition_summary: "ok" }]
        },
        {
          section_id: "weighted_scoring",
          categories: [
            {
              category_title: "Intent",
              rules: [
                {
                  rule_id: "INT001",
                  display_name: "Started",
                  points: 12,
                  condition_summary: "started"
                }
              ]
            }
          ]
        }
      ]
    });

    expect(checks).toEqual([
      { rule_id: "HF001", name: "Consent", type: "hard_filter", summary: "ok" },
      {
        rule_id: "INT001",
        name: "Started",
        type: "scoring",
        category: "Intent",
        points: 12,
        summary: "started"
      }
    ]);
  });

  it("maps message styles for selector controls", () => {
    const styles = mapMessageStyles({
      tone_selection_rules: [
        {
          tone_id: "warm_assisted",
          display_name: "Warm Assisted",
          best_for: ["Inquiry"],
          style: "Helpful",
          sample_opening: "Hi"
        }
      ]
    });

    expect(styles[0].tone_id).toBe("warm_assisted");
  });
});
