[CmdletBinding()]
param(
    [string]$Prompt = "help",
    [string]$SessionId = ""
)

$ErrorActionPreference = "Stop"

$arguments = @("invoke", "--runtime", "BusinessNextLoanAgent", $Prompt)

if ($SessionId) {
    $arguments += @("--session-id", $SessionId)
}

& agentcore @arguments
