import { NextResponse } from "next/server";

import { loadCustomers } from "@/lib/server/data";
import type { CustomerFilters } from "@/lib/types";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const filters: Partial<CustomerFilters> = {
    search: searchParams.get("search") ?? "",
    segments: listParam(searchParams, "segment"),
    cities: listParam(searchParams, "city"),
    employmentTypes: listParam(searchParams, "employment"),
    loanIntentOnly: searchParams.get("loanIntentOnly") === "true",
    highValueOnly: searchParams.get("highValueOnly") === "true",
    contactableOnly: searchParams.get("contactableOnly") === "true"
  };
  return NextResponse.json({ customers: await loadCustomers(filters) });
}

function listParam(searchParams: URLSearchParams, key: string): string[] {
  return searchParams
    .getAll(key)
    .flatMap((value) => value.split(","))
    .map((value) => value.trim())
    .filter(Boolean);
}
