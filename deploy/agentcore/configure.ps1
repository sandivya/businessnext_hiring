[CmdletBinding()]
param(
    [string]$AgentName = "businessnext-loan-agent",
    [string]$Region = "ap-south-1",
    [string]$ExecutionRoleArn = ""
)

$ErrorActionPreference = "Stop"

$arguments = @(
    "configure",
    "--entrypoint", "main.py",
    "--name", $AgentName,
    "--deployment-type", "direct_code_deploy",
    "--runtime", "PYTHON_3_13",
    "--region", $Region,
    "--disable-memory",
    "--idle-timeout", "900",
    "--max-lifetime", "3600",
    "--non-interactive"
)

if ($ExecutionRoleArn) {
    $arguments += @("--execution-role", $ExecutionRoleArn)
}

& agentcore @arguments
