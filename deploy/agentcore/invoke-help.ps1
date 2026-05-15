[CmdletBinding()]
param(
    [string]$SessionId = ""
)

$ErrorActionPreference = "Stop"

$payload = @{ prompt = "help" } | ConvertTo-Json -Compress
$arguments = @("invoke", $payload)

if ($SessionId) {
    $arguments += @("--session-id", $SessionId)
}

& agentcore @arguments
