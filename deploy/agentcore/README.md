# AgentCore Deployment Pack

This folder contains deployment support files for the prompt-only AgentCore runtime.
The repository intentionally uses the AgentCore CLI to create the generated
`agentcore/agentcore.json` file so the project stays aligned with the installed CLI version.

## Prerequisites

- AWS CLI configured with a role that can deploy AgentCore resources.
- `uv` installed.
- Node.js/npm installed for `npm install -g @aws/agentcore`.
- Bedrock model access for `openai.gpt-oss-safeguard-120b` in `ap-south-1`.
- CloudWatch Transaction Search enabled once per account if traces should be searchable.

## Configure

```powershell
.\deploy\agentcore\configure.ps1 `
  -ExecutionRoleArn "arn:aws:iam::<account-id>:role/<agentcore-runtime-role>"
```

If you omit `-ExecutionRoleArn`, the AgentCore CLI can auto-create a runtime role if your
deployment identity has the required IAM permissions.

## Deploy

```powershell
.\deploy\agentcore\deploy.ps1
```

## Invoke

```powershell
.\deploy\agentcore\invoke-help.ps1
```

## Observability

Run this once per account/region before expecting AgentCore trace search in CloudWatch:

```powershell
.\deploy\agentcore\observability-setup.ps1 -AccountId "<account-id>"
```

The app emits structured JSON logs with `request_id`, `trace_id`, `session_id`, operation,
latency, status, event count, and error type. AgentCore Runtime adds managed metrics/traces
when observability is enabled.
