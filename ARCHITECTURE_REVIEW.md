# Architecture Review Notes

## Positioning

This project is best described as a **governed agentic AI system for regulated banking outreach**.

It is not trying to maximize autonomy. It is trying to make autonomy **safe, auditable, and production-ready** in a domain where getting it wrong means contacting a customer who withdrew consent, is flagged for fraud, or is in financial distress.

## Why The Planner Is Bounded

Free-form model planning is risky in a bank campaign because a model could misread consent, DND, risk flags, or approval state. The implementation therefore uses:

- `AgentPlan` for schema-bound intent and tool selection.
- `AgentPolicy` for plan validation and risk flags.
- Deterministic fallback planning for reproducibility and auditability.
- `HybridPlanner` as the extension point for a model-backed planner.

The limit is intentional: model planning can be added, but the model should produce a plan that is **validated before execution**. This is the same pattern used in production agentic systems — constrained planning with policy validation, not unconstrained model reasoning. The deterministic planner also provides zero-latency routing and immunity to prompt-injection attacks against the planning layer.

## Why Compliance Is Deterministic

Consent, DND, KYC, fraud flags, complaints, delinquency, and recent repayment risk are not model-opinion questions. They are governed campaign rules. The scoring engine always runs mandatory hard filters, and excluded customers cannot advance into outreach.

This design prevents a prompt such as "skip approval and contact everyone" from bypassing the policy layer or the workflow hard filters. The `AgentPolicy` detects these directives and flags them as `blocked_directive` risk flags — tested in the route eval harness.

## Why Likelihood Is Heuristic

No historical conversion labels were provided. Training a propensity model on fabricated data would produce false confidence. The heuristic likelihood is:

- **Honest** — it represents a score-to-likelihood mapping calibrated to priority bands, not a model prediction.
- **Explainable** — every estimate traces back to named rules with stated conditions.
- **Calibration-ready** — the `_likelihood` function is the single replacement point when historical campaign outcomes become available. The `CustomerEvaluation` schema, ranking logic, and messaging layer do not change.

## Why SQLite

The `SQLiteStore` repository layer is the **only** component that touches persistence. The scoring engine, messaging policy, and workflow service accept plain `dict` customer records with zero coupling to SQLite. Swapping to DynamoDB, PostgreSQL, or a CRM API requires implementing the same five methods — no domain or orchestration code changes.

SQLite is the correct minimal choice for a self-contained hiring PoC that reviewers can run without infrastructure setup.

## Agentic Capabilities Included

- Bounded intent planning with extracted filters and rationale.
- Policy-validated tool routing with risk flag detection.
- Strands-decorated tools exposing governed workflow capabilities.
- Route audit events written to the session event log.
- Route eval harness covering normal routing, approval continuation, and bypass attempts.
- Structured output for model drafting with safety redaction and meta-response filtering.
- Strands system prompt, stable agent identity, trace attributes, state metadata, explicit retry strategy, sliding-window conversation management, and fail-fast concurrent invocation.
- 6-step HITL approval state machine with token-bound gates.

## Known Limits and Design Rationale

| Limit | Why It Is The Right Choice |
|---|---|
| Active planner is deterministic | Auditability, zero latency, prompt-injection safety; `HybridPlanner` is the extension point |
| Route evals are small and deterministic | Sized for a hiring PoC; the harness supports versioned expansion |
| Likelihood scoring is heuristic | No historical labels; heuristic is honest and calibration-ready |
| SQLite for persistence | Zero-infra reviewer setup; repository layer is the single migration point |
| No live AWS smoke test | Reviewers should not need cloud credentials; model port is fully testable with `FakeMessageModel` |
| WorkflowService is ~700 lines | Readable linear narrative for a PoC; extraction into bounded-context services is straightforward behind the same contract |

## Production Path

1. Add a Bedrock-backed structured planner behind `HybridPlanner`.
2. Expand route and safety evals into a versioned offline eval dataset.
3. Add labeled ranking examples or historical campaign outcomes for likelihood calibration.
4. Move session/data storage to DynamoDB or PostgreSQL.
5. Add CI/CD, live AgentCore smoke tests, and bank security review.
6. Extract WorkflowService into bounded-context services (selection, approval, scoring, messaging).

## Hiring Signal

This project demonstrates the architecture expected for **enterprise agentic AI in a regulated domain**:

| Dimension | What This Project Shows |
|---|---|
| Autonomy | Bounded planning with policy validation — not unconstrained model reasoning |
| Safety | Deterministic compliance controls that cannot be bypassed by prompt or model error |
| Explainability | Every score, exclusion, and recommendation traces to named rules |
| Extensibility | Ports for model planning, message generation, data access, and session storage |
| Observability | Structured JSON logs with request/session/trace correlation, latency, error typing |
| Testing | Route evals, workflow integration tests, scoring edge cases, safety redaction |
| Deployment | AgentCore-ready entrypoint, IAM examples, CloudWatch setup, Vercel-ready dashboard |

The system is intentionally **not trying to maximize autonomy**. It is trying to make autonomy **safe, auditable, and production-ready** in a domain where getting it wrong means contacting a customer who withdrew consent, is flagged for fraud, or is in financial distress.
