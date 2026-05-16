import { describe, expect, it, vi } from "vitest";

describe("agent invoke API", () => {
  it("validates the prompt", async () => {
    const { POST } = await import("./route");
    const response = await POST(
      new Request("http://localhost/api/agent/invoke", {
        method: "POST",
        body: JSON.stringify({ prompt: "" })
      })
    );

    expect(response.status).toBe(400);
  });

  it("returns a mocked AgentCore response when configured", async () => {
    vi.stubEnv("DASHBOARD_USE_MOCK_AGENT", "true");
    const { POST } = await import("./route");
    const response = await POST(
      new Request("http://localhost/api/agent/invoke", {
        method: "POST",
        body: JSON.stringify({ prompt: "Find premium customers" })
      })
    );
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.status).toBe("needs_approval");
    vi.unstubAllEnvs();
  });
});
