"use client";

import { Search, SlidersHorizontal } from "lucide-react";

import type { CustomerFilters, CustomerSummary } from "@/lib/types";

type Props = {
  customers: CustomerSummary[];
  filters: CustomerFilters;
  objective: string;
  onChange: (filters: CustomerFilters) => void;
  onObjectiveChange: (objective: string) => void;
};

export function FilterBar({
  customers,
  filters,
  objective,
  onChange,
  onObjectiveChange
}: Props) {
  const segments = unique(customers.map((customer) => customer.segment));
  const cities = unique(customers.map((customer) => customer.city));
  const employmentTypes = unique(customers.map((customer) => customer.employmentType));

  return (
    <section className="filter-bar" aria-label="Customer filters">
      <div className="filter-heading">
        <SlidersHorizontal size={17} aria-hidden />
        <h2>Customer cohort</h2>
      </div>
      <label className="search-box">
        <Search size={16} aria-hidden />
        <input
          value={filters.search}
          placeholder="Search name, city, segment, customer ID"
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
        />
      </label>
      <select
        aria-label="Segment"
        value={filters.segments[0] ?? ""}
        onChange={(event) =>
          onChange({ ...filters, segments: event.target.value ? [event.target.value] : [] })
        }
      >
        <option value="">All segments</option>
        {segments.map((segment) => (
          <option key={segment} value={segment}>
            {segment}
          </option>
        ))}
      </select>
      <select
        aria-label="City"
        value={filters.cities[0] ?? ""}
        onChange={(event) =>
          onChange({ ...filters, cities: event.target.value ? [event.target.value] : [] })
        }
      >
        <option value="">All cities</option>
        {cities.map((city) => (
          <option key={city} value={city}>
            {city}
          </option>
        ))}
      </select>
      <select
        aria-label="Employment"
        value={filters.employmentTypes[0] ?? ""}
        onChange={(event) =>
          onChange({
            ...filters,
            employmentTypes: event.target.value ? [event.target.value] : []
          })
        }
      >
        <option value="">All employment</option>
        {employmentTypes.map((employment) => (
          <option key={employment} value={employment}>
            {employment}
          </option>
        ))}
      </select>
      <label className="toggle">
        <input
          type="checkbox"
          checked={filters.loanIntentOnly}
          onChange={(event) => onChange({ ...filters, loanIntentOnly: event.target.checked })}
        />
        Loan intent
      </label>
      <label className="toggle">
        <input
          type="checkbox"
          checked={filters.highValueOnly}
          onChange={(event) => onChange({ ...filters, highValueOnly: event.target.checked })}
        />
        High value
      </label>
      <label className="toggle">
        <input
          type="checkbox"
          checked={filters.contactableOnly}
          onChange={(event) => onChange({ ...filters, contactableOnly: event.target.checked })}
        />
        Contactable
      </label>
      <input
        className="objective-input"
        value={objective}
        onChange={(event) => onObjectiveChange(event.target.value)}
        aria-label="Workflow objective"
      />
    </section>
  );
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right));
}
