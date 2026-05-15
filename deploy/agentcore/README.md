# AgentCore Deployment Pack

This folder contains helper scripts for the prompt-only AgentCore runtime. The actual
AgentCore project config lives in the repo-root `agentcore/` directory.

## Prerequisites

- AWS CLI configured with a role that can deploy AgentCore resources.
- `uv` installed.
- Node.js/npm installed for `npm install -g @aws/agentcore`.
- Bedrock model access for `openai.gpt-oss-safeguard-120b` in `ap-south-1`.
- CloudWatch Transaction Search enabled once per account if traces should be searchable.

## Configure

```powershell
.\deploy\agentcore\configure.ps1 `
  -AccountId "<account-id>" `
  -Region "ap-south-1"
```

This updates `agentcore/aws-targets.json`, validates the AgentCore project, and packages
the CodeZip artifact.

## Deploy

```powershell
.\deploy\agentcore\deploy.ps1
```

Use `-DryRun` to preview the deployment:

```powershell
.\deploy\agentcore\deploy.ps1 -DryRun
```

The first deploy may bootstrap CDK in the target account. The deployment identity needs
permissions to create/update/delete the `CDKToolkit` bootstrap stack and create the
AgentCore runtime resources.

## CDK Bootstrap Troubleshooting

If deployment fails because the `CDKToolkit` stack is in `ROLLBACK_FAILED`, ask an AWS
administrator to either fix/delete that bootstrap stack or grant temporary CDK bootstrap
permissions to the deployment identity. At minimum, the user/role needs CloudFormation
permissions for the bootstrap stack plus the IAM/S3/ECR permissions CDK uses to create
deployment assets.

For this project, the observed bootstrap blockers were:

- `ecr:CreateRepository` for `cdk-hnb659fds-container-assets-<account-id>-ap-south-1`.
- SSM Parameter Store write/delete access for `/cdk-bootstrap/hnb659fds/version`.
- CloudFormation access to recover or delete the failed `CDKToolkit` stack.

After permissions are fixed, clean up the failed bootstrap stack and rerun:

```powershell
aws cloudformation delete-stack --region ap-south-1 --stack-name CDKToolkit
.\deploy\agentcore\deploy.ps1
```

## Invoke

```powershell
.\deploy\agentcore\invoke-help.ps1
```

The caller that checks status or invokes the deployed runtime needs AgentCore
runtime permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock-agentcore:GetAgentRuntime",
    "bedrock-agentcore:InvokeAgentRuntime"
  ],
  "Resource": "arn:aws:bedrock-agentcore:ap-south-1:<account-id>:runtime/*"
}
```

## Observability

Run this once per account/region before expecting AgentCore trace search in CloudWatch:

```powershell
.\deploy\agentcore\observability-setup.ps1 -AccountId "<account-id>"
```

The app emits structured JSON logs with `request_id`, `trace_id`, `session_id`, operation,
latency, status, event count, and error type. AgentCore Runtime adds managed metrics/traces
when observability is enabled.
