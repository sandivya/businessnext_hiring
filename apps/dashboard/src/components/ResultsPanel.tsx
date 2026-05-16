"use client";

import { AlertTriangle, MessageSquareText, Route, ShieldCheck, Trophy } from "lucide-react";

import { formatCurrency } from "@/lib/format";
import type {
  AgentResponse,
  AgenticRoute,
  ExcludedCustomer,
  MessageDraft,
  TopCustomer
} from "@/lib/types";

type Props = {
  response: AgentResponse | null;
};

export function ResultsPanel({ response }: Props) {
  const result = response?.structured_result ?? {};
  const topCustomers = (result.top_customers as TopCustomer[] | undefined) ?? [];
  const excludedCustomers = (result.excluded_customers as ExcludedCustomer[] | undefined) ?? [];
  const selectedCheckIds = (result.selected_check_ids as string[] | undefined) ?? [];
  const agenticRoute = result.agentic_route as AgenticRoute | undefined;
  const drafts = (result.drafts as MessageDraft[] | undefined) ?? [];

  if (
    !response ||
    (topCustomers.length === 0 && excludedCustomers.length === 0 && drafts.length === 0 && !agenticRoute)
  ) {
    return (
      <section className="results-panel empty">
        <Trophy size={18} aria-hidden />
        <p>Shortlist, suppressed accounts, agent route, and outreach drafts will appear here.</p>
      </section>
    );
  }

  return (
    <section className="results-panel" aria-label="Agent results">
      {topCustomers.length > 0 ? (
        <div>
          <div className="section-title">
            <Trophy size={17} aria-hidden />
            <h2>Eligible outreach shortlist</h2>
          </div>
          <div className="table-scroll short">
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Score</th>
                  <th>Likelihood</th>
                  <th>Priority</th>
                  <th>Channel</th>
                  <th>Offer</th>
                  <th>Next action</th>
                </tr>
              </thead>
              <tbody>
                {topCustomers.map((customer) => (
                  <tr key={customer.customer_id}>
                    <td>
                      <strong>{customer.name}</strong>
                      <span>{customer.customer_id}</span>
                    </td>
                    <td>{customer.score}</td>
                    <td>{customer.likelihood_pct}%</td>
                    <td><span className="pill success">{customer.priority}</span></td>
                    <td>{customer.recommended_channel ?? "Review"}</td>
                    <td>{formatCurrency(customer.offer_amount)}</td>
                    <td>{customer.next_action ?? "Plan outreach"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selectedCheckIds.length > 0 ? (
            <div className="inline-tags" aria-label="Selected scoring checks">
              {selectedCheckIds.map((id) => <span key={id}>{id}</span>)}
            </div>
          ) : null}
          <div className="reason-grid">
            {topCustomers.map((customer) => (
              <article key={`${customer.customer_id}-reasons`}>
                <strong>{customer.name}</strong>
                <div className="inline-tags">
                  {(customer.reason_codes ?? ["Eligible high-potential account"]).map((reason) => (
                    <span key={reason}>{reason}</span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {excludedCustomers.length > 0 ? (
        <div>
          <div className="section-title">
            <ShieldCheck size={17} aria-hidden />
            <h2>Suppressed by policy</h2>
          </div>
          <div className="suppression-list">
            {excludedCustomers.map((customer) => (
              <article key={customer.customer_id}>
                <strong>{customer.name}</strong>
                <span>{customer.customer_id}</span>
                <p>{customer.failed_hard_filters.join(", ")}</p>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {agenticRoute ? (
        <div className="route-panel">
          <div className="section-title">
            <Route size={17} aria-hidden />
            <h2>Agent route</h2>
          </div>
          <dl>
            <div><dt>Intent</dt><dd>{agenticRoute.intent}</dd></div>
            <div><dt>Tool</dt><dd>{agenticRoute.tool_name}</dd></div>
            <div><dt>Reason</dt><dd>{agenticRoute.rationale}</dd></div>
          </dl>
          {agenticRoute.risk_flags?.length ? (
            <div className="risk-flags">
              <AlertTriangle size={15} aria-hidden />
              {agenticRoute.risk_flags.map((flag) => <span key={flag}>{flag}</span>)}
            </div>
          ) : null}
        </div>
      ) : null}

      {drafts.length > 0 ? (
        <div>
          <div className="section-title">
            <MessageSquareText size={17} aria-hidden />
            <h2>Message drafts</h2>
          </div>
          <div className="draft-grid">
            {drafts.map((draft) => (
              <article className="draft-card" key={`${draft.customer_id}-${draft.template_id}`}>
                <div>
                  <strong>{draft.customer_id}</strong>
                  <span>{draft.channel}</span>
                </div>
                {draft.subject ? <h3>{draft.subject}</h3> : null}
                <p>{draft.body}</p>
                <small>{draft.cta}</small>
                {draft.source_evidence.length > 0 ? (
                  <div className="inline-tags">
                    {draft.source_evidence.map((evidence) => <span key={evidence}>{evidence}</span>)}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
