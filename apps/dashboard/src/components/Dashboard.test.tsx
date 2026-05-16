import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Dashboard } from "@/components/Dashboard";

const customer = {
  customerId: "CUST0001",
  fullName: "Aarav Verma",
  age: 36,
  city: "Nagpur",
  state: "Maharashtra",
  segment: "Premium",
  employmentType: "Salaried",
  monthlyIncome: 105000,
  totalRelationshipValue: 3205000,
  bureauScore: 778,
  internalRiskBand: "Low",
  preferredContactChannel: "Push Notification",
  marketingConsent: true,
  dndFlag: false,
  highValue: true,
  contactable: true,
  loanIntentSignals: ["Incomplete application"],
  detailGroups: [{ title: "Profile", items: [{ label: "Age", value: "36" }] }]
};

describe("Dashboard", () => {
  it("runs the selected customer workflow", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/customers") {
        return jsonResponse({ customers: [customer] });
      }
      if (url === "/api/catalog") {
        return jsonResponse({ checks: [], styles: [], fields: {} });
      }
      if (url === "/api/agent/invoke") {
        expect(String(init?.body)).toContain("CUST0001");
        return jsonResponse({
          session_id: "S1",
          status: "needs_approval",
          message: "Approve customer selection",
          suggested_prompts: ["approve tok"],
          approval_token: "tok",
          events: [{ event_type: "approval_requested", message: "Approval requested", payload: {} }],
          structured_result: { customer_count: 1 }
        });
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Dashboard />);

    await screen.findByText("Aarav Verma");
    await userEvent.click(screen.getByLabelText("Select Aarav Verma"));
    await userEvent.click(screen.getByRole("button", { name: /Score selected/ }));

    await waitFor(() => expect(screen.getByText("Approve customer selection")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Approve cohort evaluation/ })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("resets active workflow progress when selection changes", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/customers") {
        return jsonResponse({
          customers: [
            customer,
            { ...customer, customerId: "CUST0002", fullName: "Neha Mehta" }
          ]
        });
      }
      if (url === "/api/catalog") {
        return jsonResponse({ checks: [], styles: [], fields: {} });
      }
      if (url === "/api/agent/invoke") {
        expect(String(init?.body)).toContain("CUST0001");
        return jsonResponse({
          session_id: "S1",
          status: "needs_approval",
          message: "Approve customer selection",
          suggested_prompts: ["approve tok"],
          approval_token: "tok",
          events: [{ event_type: "approval_requested", message: "Approval requested", payload: {} }],
          structured_result: { customer_count: 1 }
        });
      }
      throw new Error(`Unexpected fetch ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Dashboard />);

    await screen.findByText("Aarav Verma");
    await userEvent.click(screen.getByLabelText("Select Aarav Verma"));
    await userEvent.click(screen.getByRole("button", { name: /Score selected/ }));

    await screen.findByText("Approve customer selection");
    await userEvent.click(screen.getByLabelText("Select Neha Mehta"));

    expect(screen.queryByText("Approve customer selection")).not.toBeInTheDocument();
    expect(screen.queryByText("Approval requested")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" }
  });
}
