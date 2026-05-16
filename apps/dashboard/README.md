# BusinessNext Agentic Dashboard

Next.js dashboard for operating the deployed BusinessNext AgentCore loan outreach agent.

## Run Locally

```powershell
npm install
copy .env.example .env.local
npm run dev
```

Required environment:

- `AGENTCORE_RUNTIME_ARN`: deployed AgentCore runtime ARN.
- `AWS_REGION`: `ap-south-1`.
- `DASHBOARD_PASSWORD`: simple demo password for the app gate.
- `DASHBOARD_DATA_DIR`: path to the seed data directory, usually `../../data/seed`.

## What It Provides

- Customer grid with filters, row selection, and detail drawer.
- Guided workflow controls for selected customers or filtered cohorts.
- Server-side AgentCore adapter using `@aws-sdk/client-bedrock-agentcore`.
- Approval buttons for HITL workflow steps.
- Ranked shortlist, message drafts, and workflow event timeline.

The browser never receives AWS credentials. All AgentCore calls are made from Next.js route handlers.

## Quality Gates

```powershell
npm run typecheck
npm test
npm run build
npm audit
```
