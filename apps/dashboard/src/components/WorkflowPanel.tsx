"use client";

import { CheckCircle2, ListChecks, MessageSquareText, Play } from "lucide-react";
import { useMemo, useState } from "react";

import {
  buildApprovalPrompt,
  buildCheckApprovalPrompt,
  buildToneApprovalPrompt
} from "@/lib/prompts";
import type { AgentResponse, CatalogResponse } from "@/lib/types";

type Props = {
  catalog: CatalogResponse | null;
  response: AgentResponse | null;
  loading: boolean;
  selectedCount: number;
  visibleCount: number;
  onRunSelected: () => void;
  onRunFiltered: () => void;
  onInvoke: (prompt: string) => void;
};

export function WorkflowPanel({
  catalog,
  response,
  loading,
  selectedCount,
  visibleCount,
  onRunSelected,
  onRunFiltered,
  onInvoke
}: Props) {
  const [selectedChecks, setSelectedChecks] = useState<string[]>([]);
  const [selectedTone, setSelectedTone] = useState("warm_assisted");
  const approvalToken = response?.approval_token;
  const checks = useMemo(() => catalog?.checks ?? [], [catalog]);
  const scoringChecks = checks.filter((check) => check.type === "scoring");
  const needsCheckApproval = Boolean(
    approvalToken && response?.structured_result?.checks && response.status === "needs_approval"
  );
  const needsToneApproval = Boolean(
    approvalToken && response?.structured_result?.styles && response.status === "needs_approval"
  );

  function approve() {
    if (!approvalToken) {
      return;
    }
    if (needsCheckApproval) {
      const ids = selectedChecks.length > 0 ? selectedChecks : scoringChecks.map((check) => check.rule_id);
      onInvoke(buildCheckApprovalPrompt(approvalToken, ids));
      return;
    }
    if (needsToneApproval) {
      onInvoke(buildToneApprovalPrompt(approvalToken, selectedTone));
      return;
    }
    onInvoke(buildApprovalPrompt(approvalToken));
  }

  return (
    <section className="panel-section workflow-panel">
      <div className="section-title">
        <Play size={17} aria-hidden />
        <h2>Agent workflow</h2>
      </div>
      <div className="run-actions">
        <button
          className="primary-action"
          onClick={onRunSelected}
          disabled={loading || selectedCount === 0}
        >
          <Play size={16} aria-hidden />
          Run selected ({selectedCount})
        </button>
        <button className="secondary-action" onClick={onRunFiltered} disabled={loading}>
          <ListChecks size={16} aria-hidden />
          Run cohort ({visibleCount})
        </button>
      </div>

      {response ? (
        <div className={`agent-response ${response.status}`}>
          <span className="status-chip">{response.status.replace("_", " ")}</span>
          <p>{response.message}</p>
        </div>
      ) : null}

      {needsCheckApproval ? (
        <div className="approval-block">
          <h3>Scoring checks</h3>
          <div className="check-list">
            {scoringChecks.map((check) => (
              <label key={check.rule_id}>
                <input
                  type="checkbox"
                  checked={selectedChecks.includes(check.rule_id)}
                  onChange={(event) =>
                    setSelectedChecks((current) =>
                      event.target.checked
                        ? [...current, check.rule_id]
                        : current.filter((id) => id !== check.rule_id)
                    )
                  }
                />
                <span>{check.rule_id}</span>
                {check.name}
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {needsToneApproval ? (
        <div className="approval-block">
          <h3>Message style</h3>
          <div className="tone-grid">
            {(catalog?.styles ?? []).map((style) => (
              <button
                key={style.tone_id}
                className={selectedTone === style.tone_id ? "tone selected" : "tone"}
                onClick={() => setSelectedTone(style.tone_id)}
                type="button"
              >
                <strong>{style.display_name}</strong>
                <span>{style.style}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {approvalToken ? (
        <button className="primary-action full-width" onClick={approve} disabled={loading}>
          <CheckCircle2 size={16} aria-hidden />
          Approve next step
        </button>
      ) : null}

      {loading ? <p className="muted">Working with AgentCore...</p> : null}
      <div className="catalog-mini">
        <MessageSquareText size={15} aria-hidden />
        <span>{catalog?.styles.length ?? 0} outreach styles available</span>
      </div>
    </section>
  );
}
