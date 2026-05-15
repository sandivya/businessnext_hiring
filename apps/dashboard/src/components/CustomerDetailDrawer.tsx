"use client";

import { X } from "lucide-react";

import type { CustomerSummary } from "@/lib/types";

type Props = {
  customer: CustomerSummary | null;
  onClose: () => void;
};

export function CustomerDetailDrawer({ customer, onClose }: Props) {
  if (!customer) {
    return null;
  }
  return (
    <div className="drawer-backdrop" role="presentation" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label={`${customer.fullName} details`} onClick={(event) => event.stopPropagation()}>
        <header>
          <div>
            <p className="eyebrow">{customer.customerId}</p>
            <h2>{customer.fullName}</h2>
          </div>
          <button className="icon-button" onClick={onClose} title="Close details">
            <X size={16} aria-hidden />
          </button>
        </header>
        {customer.detailGroups.map((group) => (
          <section key={group.title}>
            <h3>{group.title}</h3>
            <dl>
              {group.items.map((item) => (
                <div key={item.label}>
                  <dt>{item.label}</dt>
                  <dd>{item.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </aside>
    </div>
  );
}
