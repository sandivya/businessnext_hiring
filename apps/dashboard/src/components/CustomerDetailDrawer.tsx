"use client";

import { X } from "lucide-react";

import { formatCurrency } from "@/lib/format";
import type { CustomerSummary, TopCustomer } from "@/lib/types";

type Props = {
  customer: CustomerSummary | null;
  recommendation?: TopCustomer;
  onClose: () => void;
};

export function CustomerDetailDrawer({ customer, recommendation, onClose }: Props) {
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
        {recommendation ? (
          <section className="ai-recommendation">
            <h3>AI recommendation</h3>
            <dl>
              <div><dt>Priority</dt><dd>{recommendation.priority}</dd></div>
              <div><dt>Score</dt><dd>{recommendation.score}</dd></div>
              <div><dt>Likelihood</dt><dd>{recommendation.likelihood_pct}%</dd></div>
              <div><dt>Offer</dt><dd>{formatCurrency(recommendation.offer_amount)}</dd></div>
              <div><dt>Channel</dt><dd>{recommendation.recommended_channel ?? "Review"}</dd></div>
              <div><dt>Next action</dt><dd>{recommendation.next_action ?? "Plan outreach"}</dd></div>
            </dl>
            <div className="inline-tags">
              {(recommendation.reason_codes ?? []).map((reason) => <span key={reason}>{reason}</span>)}
            </div>
          </section>
        ) : null}
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
