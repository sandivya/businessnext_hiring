import { describe, expect, it, vi } from "vitest";

import { isPublicPath, sessionTokenForPassword, validSessionToken } from "@/lib/auth";

describe("dashboard auth helpers", () => {
  it("validates hashed session tokens", async () => {
    vi.stubEnv("DASHBOARD_PASSWORD", "secret");
    const token = await sessionTokenForPassword("secret");

    await expect(validSessionToken(token)).resolves.toBe(true);
    await expect(validSessionToken("bad")).resolves.toBe(false);
    vi.unstubAllEnvs();
  });

  it("allows only public paths before authentication", () => {
    expect(isPublicPath("/login")).toBe(true);
    expect(isPublicPath("/api/auth/login")).toBe(true);
    expect(isPublicPath("/")).toBe(false);
  });
});
