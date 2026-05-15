# Agent Workflow

This document shows how the prompt-only AgentCore agent moves from a business request to an approved customer shortlist and safe outreach drafts.

## End-To-End Flow

```mermaid
flowchart TD
    Start([User sends prompt]) --> Runtime[AgentCore Runtime / main.py]
    Runtime --> Validate[Validate AgentRequest]
    Validate --> Help{Help, catalog, or workflow?}

    Help -->|Help / unclear| Capabilities[Show capabilities, examples, fields, checks, message styles]
    Help -->|Catalog prompt| Catalog[Show requested catalog]
    Help -->|Campaign prompt| SelectionApproval[Ask approval for customer selection]

    SelectionApproval --> SelectionToken[Return approval token]
    SelectionToken --> SelectionApproved{approve token?}
    SelectionApproved -->|No| Reminder[Remind user what approval is pending]
    SelectionApproved -->|Yes| SelectCustomers[Select customers using available fields and direct intent signals]

    SelectCustomers --> CheckApproval[Ask approval for checks to run]
    CheckApproval --> CheckApproved{approve token and optional rule IDs?}
    CheckApproved -->|No| Reminder
    CheckApproved -->|Yes| Score[Run hard filters, selected scoring checks, likelihood, and recommendation]

    Score --> ShortlistApproval[Ask user to accept shortlist]
    ShortlistApproval --> ShortlistApproved{approve token?}
    ShortlistApproved -->|No| Reminder
    ShortlistApproved -->|Yes| StyleChoice[Show message styles and request tone approval]

    StyleChoice --> StyleApproved{approve token + tone?}
    StyleApproved -->|No| Reminder
    StyleApproved -->|Yes| DraftApproval[Ask approval before Bedrock drafting]

    DraftApproval --> BedrockApproved{approve token?}
    BedrockApproved -->|No| Reminder
    BedrockApproved -->|Yes| Draft[Draft messages through Strands + Bedrock]

    Draft --> Safety[Apply messaging policy and sensitive-term redaction]
    Safety --> FinalApproval[Ask final approval for messages]
    FinalApproval --> FinalApproved{approve token?}
    FinalApproved -->|No| Reminder
    FinalApproved -->|Yes| Done([Return final approved outreach package])

    Runtime --> Logs[Structured JSON logs]
    SelectCustomers --> Events[Workflow events]
    Score --> Events
    Draft --> Events
    Events --> Timeline[Future frontend activity timeline]
    Logs --> CloudWatch[AgentCore / CloudWatch Observability]
```

## Approval State Machine

```mermaid
stateDiagram-v2
    [*] --> Ready
    Ready --> CustomerSelectionApproval: campaign prompt
    CustomerSelectionApproval --> CheckSelectionApproval: approve token
    CheckSelectionApproval --> ShortlistAcceptanceApproval: approve token / optional check IDs
    ShortlistAcceptanceApproval --> MessageStyleApproval: approve token
    MessageStyleApproval --> BedrockDraftingApproval: approve token + tone
    BedrockDraftingApproval --> FinalMessagesApproval: approve token
    FinalMessagesApproval --> Completed: approve token

    CustomerSelectionApproval --> CustomerSelectionApproval: missing/invalid token
    CheckSelectionApproval --> CheckSelectionApproval: missing/invalid token
    ShortlistAcceptanceApproval --> ShortlistAcceptanceApproval: missing/invalid token
    MessageStyleApproval --> MessageStyleApproval: missing tone or token
    BedrockDraftingApproval --> BedrockDraftingApproval: missing/invalid token
    FinalMessagesApproval --> FinalMessagesApproval: missing/invalid token

    Ready --> CatalogResponse: help / fields / checks / styles
    CatalogResponse --> Ready
```

## Runtime Sequence

```mermaid
sequenceDiagram
    actor User
    participant AC as AgentCore Runtime
    participant Main as main.py
    participant WF as WorkflowService
    participant Repo as SQLiteStore
    participant Rules as ScoringEngine
    participant Msg as MessagingPolicy
    participant Strands as Strands Agent
    participant Bedrock as Bedrock Model
    participant Obs as JSON Logs / CloudWatch

    User->>AC: {"prompt": "Find high-value customers likely to convert"}
    AC->>Main: Invoke entrypoint
    Main->>WF: AgentRequest
    WF->>Repo: Load or create session
    WF->>Repo: Emit approval_requested event
    WF-->>User: needs_approval + approval_token
    WF->>Obs: request/session/latency/status log

    User->>AC: {"session_id": "...", "prompt": "approve <token>"}
    AC->>Main: Invoke entrypoint
    Main->>WF: AgentRequest
    WF->>Repo: Load session
    WF->>Rules: Evaluate hard filters and scoring checks
    Rules-->>WF: ranked evaluations with explanations
    WF->>Repo: Persist state and workflow events
    WF-->>User: shortlist + next approval token

    User->>AC: approve style and drafting tokens
    WF->>Msg: Build safe prompt and fallback message
    Msg->>Strands: structured draft request
    Strands->>Bedrock: invoke openai.gpt-oss-safeguard-120b
    Bedrock-->>Strands: model response
    Strands-->>Msg: structured message
    Msg-->>WF: redacted safe drafts
    WF-->>User: final drafts awaiting approval
```

## What A Future Frontend Can Reuse

- `status` to decide whether to show a normal answer, clarification prompt, or approval action.
- `approval_token` to render explicit approve buttons.
- `events` to render an activity timeline.
- `structured_result` to render tables for shortlisted customers, checks, likelihood, and draft messages.
- `structured_result.observability` to correlate a user-visible session with CloudWatch logs and AgentCore traces.
