[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$AccountId,
    [string]$Region = "ap-south-1",
    [int]$SamplingPercentage = 1
)

$ErrorActionPreference = "Stop"

$resourcePolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Sid = "TransactionSearchXRayAccess"
            Effect = "Allow"
            Principal = @{ Service = "xray.amazonaws.com" }
            Action = "logs:PutLogEvents"
            Resource = @(
                "arn:aws:logs:$Region:$AccountId:log-group:aws/spans:*",
                "arn:aws:logs:$Region:$AccountId:log-group:/aws/application-signals/data:*"
            )
            Condition = @{
                ArnLike = @{ "aws:SourceArn" = "arn:aws:xray:$Region:$AccountId:*" }
                StringEquals = @{ "aws:SourceAccount" = $AccountId }
            }
        }
    )
} | ConvertTo-Json -Depth 10 -Compress

& aws logs put-resource-policy `
    --region $Region `
    --policy-name "AgentCoreTransactionSearchXRayAccess" `
    --policy-document $resourcePolicy

& aws xray update-trace-segment-destination `
    --region $Region `
    --destination "CloudWatchLogs"

$indexingRule = @{
    Probabilistic = @{
        DesiredSamplingPercentage = $SamplingPercentage
    }
} | ConvertTo-Json -Depth 5 -Compress

& aws xray update-indexing-rule `
    --region $Region `
    --name "Default" `
    --rule $indexingRule
