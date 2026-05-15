"use client";

import { Eye } from "lucide-react";

import { formatCurrency, formatNumber } from "@/lib/format";
import type { CustomerSummary } from "@/lib/types";

type Props = {
  customers: CustomerSummary[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onOpenCustomer: (customer: CustomerSummary) => void;
};

export function CustomerTable({
  customers,
  selectedIds,
  onSelectionChange,
  onOpenCustomer
}: Props) {
  const selected = new Set(selectedIds);
  const allVisibleSelected =
    customers.length > 0 && customers.every((customer) => selected.has(customer.customerId));

  function toggle(customerId: string) {
    onSelectionChange(
      selected.has(customerId)
        ? selectedIds.filter((id) => id !== customerId)
        : [...selectedIds, customerId]
    );
  }

  function toggleAll() {
    if (allVisibleSelected) {
      onSelectionChange(selectedIds.filter((id) => !customers.some((c) => c.customerId === id)));
    } else {
      onSelectionChange(Array.from(new Set([...selectedIds, ...customers.map((c) => c.customerId)])));
    }
  }

  return (
    <section className="table-panel" aria-label="Customer list">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>
                <input
                  aria-label="Select all visible customers"
                  type="checkbox"
                  checked={allVisibleSelected}
                  onChange={toggleAll}
                />
              </th>
              <th>Customer</th>
              <th>Segment</th>
              <th>City</th>
              <th>Employment</th>
              <th>Income</th>
              <th>Relationship value</th>
              <th>Bureau</th>
              <th>Channel</th>
              <th>Consent</th>
              <th>Intent</th>
              <th aria-label="Open detail" />
            </tr>
          </thead>
          <tbody>
            {customers.map((customer) => (
              <tr key={customer.customerId}>
                <td>
                  <input
                    aria-label={`Select ${customer.fullName}`}
                    type="checkbox"
                    checked={selected.has(customer.customerId)}
                    onChange={() => toggle(customer.customerId)}
                  />
                </td>
                <td>
                  <strong>{customer.fullName}</strong>
                  <span>{customer.customerId}</span>
                </td>
                <td>{customer.segment}</td>
                <td>{customer.city}</td>
                <td>{customer.employmentType}</td>
                <td>{formatCurrency(customer.monthlyIncome)}</td>
                <td>{formatCurrency(customer.totalRelationshipValue)}</td>
                <td>{formatNumber(customer.bureauScore)}</td>
                <td>{customer.preferredContactChannel}</td>
                <td>
                  <span className={customer.contactable ? "pill success" : "pill warning"}>
                    {customer.contactable ? "Allowed" : "Suppressed"}
                  </span>
                </td>
                <td>
                  <span className={customer.loanIntentSignals.length ? "pill info" : "pill"}>
                    {customer.loanIntentSignals.length || "None"}
                  </span>
                </td>
                <td>
                  <button
                    className="icon-button"
                    title={`Open ${customer.fullName}`}
                    onClick={() => onOpenCustomer(customer)}
                  >
                    <Eye size={15} aria-hidden />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
