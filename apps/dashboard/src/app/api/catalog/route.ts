import { NextResponse } from "next/server";

import { loadCatalog } from "@/lib/server/data";

export async function GET() {
  return NextResponse.json(await loadCatalog());
}
