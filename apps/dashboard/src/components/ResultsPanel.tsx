"use client";

import { MessageSquareText, Trophy } from "lucide-react";

import { formatCurrency } from "@/lib/format";
import type { AgentResponse, CustomerEvaluation, MessageDraft } from "@/lib/types";

type Props = {
  response: AgentResponse | null;
};

export function ResultsPanel({ response }: Props) {
  const result = response?.structured_result ?? {};
  const evaluations = (result.evaluations as CustomerEvaluation[] | undefined) ?? [];
  const drafts = (result.drafts as MessageDraft[] | undefined) ?? [];

  if (!response || (evaluations.length === 0 && drafts.length === 0)) {
    return (
      <section className="results-panel empty">
        <Trophy size={18} aria-hidden />
        <p>Ranked shortlist and outreach drafts will appear here.</p>
      </section>
    );
  }

  return (
    <section className="results-panel" aria-label="Agent results">
      {evaluations.length > 0 ? (
        <div>
          <div className="section-title">
            <Trophy size={17} aria-hidden />
            <h2>Ranked shortlist</h2>
          </div>
          <div className="table-scroll short">
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Eligible</th>
                  <th>Score</th>
                  <th>Likelihood</th>
                  <th>Band</th>
                  <th>Offer</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {evaluations.map((evaluation) => (
                  <tr key={evaluation.customer_id}>
                    <td>
                      <strong>{evaluation.full_name}</strong>
                      <span>{evaluation.customer_id}</span>
                    </td>
                    <td>
                      <span className={evaluation.eligible ? "pill success" : "pill warning"}>
                        {evaluation.eligible ? "Yes" : "No"}
                      </span>
                    </td>
                    <td>{evaluation.score}</td>
                    <td>{evaluation.heuristic_likelihood_pct}%</td>
                    <td>{evaluation.priority_label}</td>
                    <td>{formatCurrency(evaluation.recommendation.amount)}</td>
                    <td>{evaluation.recommendation.suggested_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
