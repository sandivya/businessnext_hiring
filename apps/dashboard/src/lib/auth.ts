export const DASHBOARD_COOKIE = "businessnext_dashboard";

export function dashboardPassword(): string {
  return process.env.DASHBOARD_PASSWORD || "businessnext-demo";
}

export async function sessionTokenForPassword(password: string): Promise<string> {
  const bytes = new TextEncoder().encode(`businessnext-dashboard:${password}`);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function validSessionToken(token: string | undefined | null): Promise<boolean> {
  if (!token) {
    return false;
  }
  return token === (await sessionTokenForPassword(dashboardPassword()));
}

export function isPublicPath(pathname: string): boolean {
  return (
    pathname === "/login" ||
    pathname === "/api/auth/login" ||
    pathname.startsWith("/_next") ||
    pathname === "/favicon.ico"
  );
}
