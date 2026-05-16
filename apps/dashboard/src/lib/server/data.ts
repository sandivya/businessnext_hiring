import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

import { fieldCatalog, mapChecks, mapMessageStyles } from "@/lib/catalog";
import { filterCustomers, mapCustomerSummary } from "@/lib/customers";
import type { CatalogResponse, CustomerFilters, CustomerSummary } from "@/lib/types";

type CustomerSeed = {
  customers: Record<string, unknown>[];
};

const DATA_DIR = process.env.DASHBOARD_DATA_DIR
  ? path.resolve(process.env.DASHBOARD_DATA_DIR)
  : path.resolve(process.cwd(), "../../data/seed");

export async function loadCustomers(filters?: Partial<CustomerFilters>): Promise<CustomerSummary[]> {
  const seed = await readJson<CustomerSeed>("fabricated_bank_customers_poc_100.json");
  const customers = seed.customers.map(mapCustomerSummary);
  if (!filters) {
    return customers;
  }
  return filterCustomers(customers, {
    search: filters.search ?? "",
    segments: filters.segments ?? [],
    cities: filters.cities ?? [],
    employmentTypes: filters.employmentTypes ?? [],
    loanIntentOnly: Boolean(filters.loanIntentOnly),
    highValueOnly: Boolean(filters.highValueOnly),
    contactableOnly: Boolean(filters.contactableOnly)
  });
}

export async function loadCatalog(): Promise<CatalogResponse> {
  const [shortlisting, messaging] = await Promise.all([
    readJson<Record<string, any>>("personal_loan_shortlisting_rules_ui_ready.json"),
    readJson<Record<string, any>>("personlaised_messaging_rules.json")
  ]);
  return {
    fields: fieldCatalog,
    checks: mapChecks(shortlisting as any),
    styles: mapMessageStyles(messaging as any)
  };
}

async function readJson<T>(fileName: string): Promise<T> {
  const content = await readFile(path.join(DATA_DIR, fileName), "utf-8");
  return JSON.parse(content) as T;
}
