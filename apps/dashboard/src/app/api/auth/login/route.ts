import { NextResponse } from "next/server";

import { DASHBOARD_COOKIE, dashboardPassword, sessionTokenForPassword } from "@/lib/auth";

export async function POST(request: Request) {
  const body = (await request.json()) as { password?: unknown };
  if (typeof body.password !== "string" || body.password !== dashboardPassword()) {
    return NextResponse.json({ error: "Invalid dashboard password." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(DASHBOARD_COOKIE, await sessionTokenForPassword(body.password), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8
  });
  return response;
}
