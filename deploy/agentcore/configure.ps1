[CmdletBinding()]
param(
    [string]$AccountId = "440744216711",
    [string]$Region = "ap-south-1",
    [string]$TargetName = "default"
)

$ErrorActionPreference = "Stop"

$targetPath = Join-Path (Get-Location) "agentcore/aws-targets.json"
$targets = @(
    @{
        name = $TargetName
        description = "Default AgentCore deployment target for the hiring project"
        account = $AccountId
        region = $Region
    }
)

$targets | ConvertTo-Json -Depth 5 | Set-Content -Path $targetPath -Encoding utf8

Push-Location "agentcore/cdk"
try {
    npm install
}
finally {
    Pop-Location
}

& agentcore validate
& agentcore package
