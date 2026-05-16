# BusinessNext Agentic Dashboard

Next.js dashboard for operating the deployed BusinessNext AgentCore loan outreach agent.

## Run Locally

```powershell
npm install
copy .env.example .env.local
npm run dev
```

Required environment:

- `AWS_REGION`: `ap-south-1`.
- `DASHBOARD_PASSWORD`: simple demo password for the app gate.
- `DASHBOARD_USE_MOCK_AGENT`: set to `true` only for a no-AWS demo.
- `AGENTCORE_RUNTIME_ARN`: deployed AgentCore runtime ARN, required when `DASHBOARD_USE_MOCK_AGENT=false`.

The dashboard includes the seed JSON files under `data/seed`, so `DASHBOARD_DATA_DIR` is optional.
Set it only if you want to load seed files from another directory.

## Deploy On Vercel Hobby

Use Vercel Hobby only for a personal or non-commercial demo.

Recommended project settings:

- Framework Preset: `Next.js`
- Root Directory: `apps/dashboard`
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: leave blank

For a no-AWS demo, add these Vercel environment variables:

```text
DASHBOARD_PASSWORD=<strong-demo-password>
DASHBOARD_USE_MOCK_AGENT=true
AWS_REGION=ap-south-1
```

For a live AgentCore demo, use:

```text
DASHBOARD_PASSWORD=<strong-demo-password>
DASHBOARD_USE_MOCK_AGENT=false
AWS_REGION=ap-south-1
AGENTCORE_RUNTIME_ARN=<runtime-arn>
AWS_ACCESS_KEY_ID=<deploy-user-or-role-key>
AWS_SECRET_ACCESS_KEY=<deploy-user-or-role-secret>
```

The AWS identity must be allowed to invoke the configured AgentCore runtime.

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
