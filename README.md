# BusinessNext Personal Loan Outreach Agent

Governed agentic AI app for identifying high-potential bank customers for a personal-loan campaign, explaining the shortlist, and drafting safe outreach only after human approval.

This project is intentionally **not a free-form autonomous agent**. It is a regulated banking design: the agent plans, routes, explains, drafts, and records decisions, while compliance-critical controls such as consent, DND, hard filters, approval tokens, and final outreach remain deterministic.

## Why This Is Agentic

- `GovernedAgentOrchestrator` turns each prompt into a bounded `AgentPlan`.
- `AgentPolicy` validates the plan, corrects tool/intent mismatches, and flags unsafe directives such as approval bypass attempts.
- Strands-decorated tools expose capabilities, field discovery, check discovery, message styles, and workflow execution.
- Route decisions are returned in `structured_result.agentic_route` and written to workflow events when a session exists.
- Route evals test tool selection, approval continuation, prompt normalization, campaign routing, and bypass attempts.
- Bedrock/Strands drafting uses structured output, retry strategy, system prompt, stable agent identity, trace attributes, state metadata, and sliding-window conversation management.

## What The Agent Does

- Finds candidate customers from the fabricated bank dataset.
- Runs mandatory hard filters and explainable weighted scoring.
- Separates eligible outreach candidates from customers excluded by compliance/risk filters.
- Estimates heuristic conversion likelihood and recommends next outreach action.
- Requires token-bound human approval before evaluation, checks, shortlist acceptance, message style, Bedrock drafting, and final messages.
- Drafts personalized messages with sensitive-trigger redaction and safe fallback templates.

## Architecture

```mermaid
flowchart TD
    User[Prompt User / AgentCore Invoke] --> Runtime[main.py / Bedrock AgentCore]
    Runtime --> Contract[AgentRequest]
    Contract --> Router[GovernedAgentOrchestrator]
    Router --> Plan[AgentPlan]
    Plan --> Policy[AgentPolicy]
    Policy --> Tools[Strands Tools]
    Tools --> Workflow[WorkflowService]
    Workflow --> Store[(SQLite sessions/events/data)]
    Workflow --> Rules[ScoringEngine]
    Workflow --> Messaging[MessagingPolicy]
    Messaging --> Strands[Strands Agent]
    Strands --> Bedrock[Bedrock Model]
    Runtime --> Logs[JSON Logs / CloudWatch]
```

## Key Design Choices

- **Governed autonomy over full autonomy:** the agent can plan and route, but cannot bypass compliance.
- **Schema-first planning:** `AgentPlan` constrains intent, tool name, prompt, extracted filters, rationale, and risk flags.
- **Policy before execution:** unsafe prompts are flagged before tools run; hard filters always run later in the workflow.
- **Deterministic core workflow:** this is deliberate for banking auditability.
- **Hybrid-ready planning:** a model-backed planner can be plugged into `HybridPlanner`; deterministic planning remains the fallback.
- **Model isolation:** message generation goes through `MessageModelPort`, so Bedrock can be faked in tests and swapped later.
- **Frontend-ready contract:** responses expose status, approval token, events, structured results, observability, and route metadata.

For a deeper hiring-review framing, see [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md). For flow diagrams, see [workflow.md](workflow.md).

## Source Layout

```text
src/businessnext_agent/
  orchestration/    Agent planner, policy, router, route evals, Strands tools
  application/      HITL workflow and state machine
  domain/           catalogs, scoring rules, messaging policy
  infrastructure/   SQLite repository and structured observability
  runtime.py        AgentCore-compatible service assembly
  schemas.py        Pydantic contracts
```

## Response Contract

Input:

```json
{
  "session_id": "optional-session-id",
  "prompt": "Find high-value customers likely to convert"
}
```

Output:

```json
{
  "session_id": "session-id",
  "status": "completed | needs_approval | needs_clarification | error",
  "message": "Plain-language response",
  "suggested_prompts": [],
  "approval_token": "only when approval is needed",
  "events": [],
  "structured_result": {
    "agentic_route": {},
    "observability": {}
  }
}
```

## Example Conversation

```json
{ "prompt": "Find high-value customers likely to convert this month" }
```

The agent returns `needs_approval` and an approval token.

```json
{ "session_id": "returned-session-id", "prompt": "approve returned-token" }
```

For check selection:

```json
{
  "session_id": "returned-session-id",
  "prompt": "approve returned-token INT001 CRD001 TIM001"
}
```

Mandatory hard filters always run, even when the user narrows optional scoring checks.

## Local Setup

```powershell
uv sync --extra dev
$env:BUSINESSNEXT_USE_FAKE_MODEL = "true"
uv run pytest
```

Local invoke:

```powershell
uv run python - <<'PY'
from businessnext_agent.runtime import invoke
print(invoke({"prompt": "help"}))
PY
```

## Quality Status

- Tests: 31
- Coverage: 100% over `src/businessnext_agent`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format --check .`
- Runtime: AgentCore-compatible `main.py`
- Deployment assets: `deploy/agentcore`, IAM examples, AgentCore config, CloudWatch setup

## Production Gaps

- Live AWS smoke test with real AgentCore/Bedrock credentials.
- Model-backed planner implementation behind `HybridPlanner`.
- Larger offline eval dataset with regression thresholds.
- Historical conversion labels for propensity calibration.
- Production data store such as DynamoDB or PostgreSQL.
- Security review, CI/CD, and bank compliance sign-off.

```powershell
.\deploy\agentcore\configure.ps1 `
  -AccountId "<account-id>" `
  -Region "ap-south-1"
```

Deploy:

```powershell
.\deploy\agentcore\deploy.ps1
```

Invoke:

```powershell
.\deploy\agentcore\invoke-help.ps1
```

The deployment pack also includes IAM examples and a one-time CloudWatch Transaction Search setup script under `deploy/agentcore`.

## Agentic Dashboard

The repository now includes a Next.js dashboard under `apps/dashboard`. It provides a customer
grid, guided AgentCore workflow controls, explicit approval buttons, ranked shortlist rendering,
message-style selection, draft review, and a workflow event timeline.

```powershell
cd apps\dashboard
npm install
copy .env.example .env.local
npm run dev
```

Set `AGENTCORE_RUNTIME_ARN`, `AWS_REGION`, and `DASHBOARD_PASSWORD` in `.env.local`. The browser
talks only to Next.js route handlers; the server-side adapter invokes AgentCore with AWS SDK
credentials from the local environment or deployment role.

For a minimal-cost hosted demo, deploy the dashboard on Vercel Hobby with project root
`apps/dashboard`. See `apps/dashboard/README.md` for the Vercel settings and required
environment variables.

## Observability

The app emits structured JSON logs to stdout with:

- `request_id`, `trace_id`, and `session_id`
- operation name
- latency in milliseconds
- status and workflow event count
- error type and stack trace for failures

AgentCore Runtime can add managed OpenTelemetry traces, metrics, and CloudWatch dashboards when observability is enabled for the account/runtime.

The app does not log full prompts, generated customer messages, or raw customer records. It logs prompt length and workflow metadata to reduce PII exposure.

## Product Readiness And Quality

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Current quality status:

- **Tests:** 21 backend tests.
- **Coverage:** 100% over `src/businessnext_agent`.
- **Linting:** Ruff check passes.
- **Formatting:** Ruff format check passes.
- **Deployment readiness:** AgentCore entrypoint, deployment scripts, IAM examples, env template, and observability setup are included.
- **Operational readiness:** structured JSON logs, request/session/trace correlation, latency, error logging, retries, safe fallback behavior, and no raw PII logging.
- **Product readiness:** strong for a hiring project / production-style PoC. For a real bank production rollout, the next steps would be live AWS validation, security review, CI/CD pipeline, production data store, and model evaluation against historical campaign outcomes.

## Trade-Offs

- Likelihood is heuristic and explainable because no historical conversion labels were provided.
- SQLite is used to keep the assignment self-contained; the repository layer is the migration point for DynamoDB/PostgreSQL.
- No live AWS smoke test is included, because this hiring project should not require reviewer AWS credentials.

## Useful Files

- `main.py`: AgentCore entrypoint.
- `src/businessnext_agent/application/workflow.py`: HITL workflow and state machine.
- `src/businessnext_agent/domain/rules.py`: scoring and likelihood logic.
- `src/businessnext_agent/domain/messaging.py`: message policy, safety redaction, Bedrock model port.
- `src/businessnext_agent/infrastructure/observability.py`: structured JSON logging.
- `deploy/agentcore`: AgentCore deployment scripts and IAM examples.
- `agent.md`: agent capabilities, HITL policy, and message safety rules.
- `workflow.md`: visual workflow, approval state machine, and runtime sequence.
  These are left explicit because the current project is a self-contained hiring PoC, not a bank production deployment.
