import { NextRequest, NextResponse } from "next/server";

import { DASHBOARD_COOKIE, isPublicPath, validSessionToken } from "@/lib/auth";

export async function proxy(request: NextRequest) {
  if (isPublicPath(request.nextUrl.pathname)) {
    return NextResponse.next();
  }
  const token = request.cookies.get(DASHBOARD_COOKIE)?.value;
  if (await validSessionToken(token)) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/((?!.*\\..*).*)"]
};
