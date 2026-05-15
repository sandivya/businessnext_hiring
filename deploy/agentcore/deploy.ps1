[CmdletBinding()]
param(
    [string]$Target = "default",
    [string]$AccountId = "440744216711",
    [string]$Region = "ap-south-1",
    [switch]$DryRun,
    [switch]$Diff,
    [switch]$VerboseEvents,
    [switch]$SkipBootstrap
)

$ErrorActionPreference = "Stop"

Push-Location "agentcore/cdk"
try {
    if (-not (Test-Path -LiteralPath "node_modules")) {
        npm install
    }

    if (-not $SkipBootstrap) {
        & .\node_modules\.bin\cdk.cmd bootstrap "aws://$AccountId/$Region" --require-approval never --no-bootstrap-customer-key
    }
}
finally {
    Pop-Location
}

& agentcore package

$arguments = @("deploy", "--target", $Target, "--yes")

if ($DryRun) {
    $arguments += "--dry-run"
}

if ($Diff) {
    $arguments += "--diff"
}

if ($VerboseEvents) {
    $arguments += "--verbose"
}

& agentcore @arguments
