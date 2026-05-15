# Architecture Review Notes

## Positioning

This project is best described as a **governed agentic AI system for regulated banking outreach**.

It is not trying to maximize autonomy. It is trying to make autonomy safe: the agent plans and routes work, but deterministic controls decide whether customers can be evaluated, shortlisted, contacted, or messaged.

## Why The Planner Is Bounded

Free-form model planning is risky in a bank campaign because a model could misread consent, DND, risk flags, or approval state. The implementation therefore uses:

- `AgentPlan` for schema-bound intent and tool selection.
- `AgentPolicy` for plan validation and risk flags.
- Deterministic fallback planning for reproducibility.
- `HybridPlanner` as the extension point for a model-backed planner.

The limit is intentional: model planning can be added, but the model should produce a plan that is validated before execution.

## Why Compliance Is Deterministic

Consent, DND, KYC, fraud flags, complaints, delinquency, and recent repayment risk are not model-opinion questions. They are governed campaign rules. The scoring engine always runs mandatory hard filters, and excluded customers cannot advance into outreach.

This design prevents a prompt such as "skip approval and contact everyone" from bypassing the policy layer or the workflow hard filters.

## Agentic Capabilities Included

- Bounded intent planning.
- Policy-validated tool routing.
- Strands-decorated tools.
- Route audit events.
- Route eval harness.
- Structured output for model drafting.
- Strands system prompt, identity, trace attributes, state, retry strategy, and sliding-window conversation management.
- HITL approval state machine.

## Known Limits

- The active planner is deterministic; a model-backed planner is an extension point.
- Route evals are small and deterministic, not a full offline benchmark suite.
- Likelihood scoring is heuristic because no historical conversion labels were provided.
- SQLite is used for portability, not production scale.
- No live AWS smoke test is included because reviewers should not need cloud credentials.

## Production Path

1. Add a Bedrock-backed structured planner behind `HybridPlanner`.
2. Expand route and safety evals into a versioned offline eval dataset.
3. Add labeled ranking examples or historical campaign outcomes.
4. Move session/data storage to DynamoDB or PostgreSQL.
5. Add CI/CD, live AgentCore smoke tests, and bank security review.
6. Integrate a frontend over the existing response contract.

## Hiring Signal

The project demonstrates the architecture expected for enterprise agentic AI:

- autonomy where it helps,
- deterministic policy where it matters,
- observability and auditability throughout,
- tests and evals around agent behavior,
- clear production migration points.
