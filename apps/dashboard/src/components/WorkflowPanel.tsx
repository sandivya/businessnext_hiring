"use client";

import { CheckCircle2, FileCheck2, ListChecks, MessageSquareText, Play } from "lucide-react";
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
  const stage = getWorkflowStage(response);

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
        <h2>Campaign workflow</h2>
      </div>
      <ol className="pipeline-steps" aria-label="Campaign workflow stages">
        {[
          "Cohort",
          "Checks",
          "Shortlist",
          "Style",
          "Drafts",
          "Final"
        ].map((label, index) => (
          <li key={label} className={index <= stage.index ? "active" : ""}>
            <span>{index + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      {!response ? (
        <div className="run-actions">
          <button
            className="primary-action"
            onClick={onRunSelected}
            disabled={loading || selectedCount === 0}
          >
            <Play size={16} aria-hidden />
            Score selected ({selectedCount})
          </button>
          <button className="secondary-action" onClick={onRunFiltered} disabled={loading}>
            <ListChecks size={16} aria-hidden />
            Score cohort ({visibleCount})
          </button>
        </div>
      ) : null}

      {response ? (
        <div className={`agent-response ${response.status}`}>
          <span className="status-chip">{response.status.replace("_", " ")}</span>
          <p>{cleanAgentMessage(response.message)}</p>
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
          {stage.icon === "file" ? <FileCheck2 size={16} aria-hidden /> : <CheckCircle2 size={16} aria-hidden />}
          {stage.action}
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

function cleanAgentMessage(message: string): string {
  return message
    .replace(/\s*Reply 'approve [^']+'[^.]*\./gi, "")
    .replace(/\s*Reply with `approve [^`]+`[^.]*\./gi, "")
    .replace(/\s*Approval token:\s*`?[\w-]+`?/gi, "")
    .trim();
}

function getWorkflowStage(response: AgentResponse | null): { index: number; action: string; icon: "check" | "file" } {
  const result = response?.structured_result ?? {};
  const workflowStage = result.workflow_stage;
  if (workflowStage === "reset") {
    return { index: -1, action: "Start new workflow", icon: "check" };
  }
  if (workflowStage === "check_selection") {
    return { index: 1, action: "Run approved checks", icon: "check" };
  }
  if (workflowStage === "shortlist_review") {
    return { index: 2, action: "Accept shortlist", icon: "check" };
  }
  if (workflowStage === "message_style") {
    return { index: 3, action: "Approve outreach style", icon: "check" };
  }
  if (workflowStage === "draft_generation") {
    return { index: 4, action: "Generate message drafts", icon: "file" };
  }
  if (workflowStage === "final_approval") {
    return { index: 5, action: "Finalize outreach package", icon: "file" };
  }
  if (!response?.approval_token) {
    return { index: 0, action: "Approve next step", icon: "check" };
  }
  if (result.checks) {
    return { index: 1, action: "Run approved checks", icon: "check" };
  }
  if (result.top_customers) {
    return { index: 2, action: "Accept shortlist", icon: "check" };
  }
  if (result.styles) {
    return { index: 3, action: "Approve outreach style", icon: "check" };
  }
  if (result.tone_id) {
    return { index: 4, action: "Generate message drafts", icon: "file" };
  }
  if (result.drafts) {
    return { index: 5, action: "Finalize outreach package", icon: "file" };
  }
  return { index: 0, action: "Approve cohort evaluation", icon: "check" };
}
