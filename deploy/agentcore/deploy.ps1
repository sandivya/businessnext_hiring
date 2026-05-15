[CmdletBinding()]
param(
    [string]$Region = "ap-south-1",
    [string]$LogLevel = "INFO",
    [bool]$UseFakeModel = $false
)

$ErrorActionPreference = "Stop"

$fakeModel = $UseFakeModel.ToString().ToLowerInvariant()

& agentcore deploy `
    --env "BUSINESSNEXT_AWS_REGION=$Region" `
    --env "BUSINESSNEXT_BEDROCK_MODEL_ID=openai.gpt-oss-safeguard-120b" `
    --env "BUSINESSNEXT_USE_FAKE_MODEL=$fakeModel" `
    --env "BUSINESSNEXT_LOG_LEVEL=$LogLevel"
