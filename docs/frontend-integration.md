# Future Frontend Integration

V1 is prompt-only through Bedrock AgentCore Runtime. A future frontend should be a thin adapter over the existing workflow contract, not a second implementation.

## Recommended UI Panels

1. Prompt and approval panel
   - Sends prompts to the AgentCore invocation adapter.
   - Displays `message`, `suggested_prompts`, and approval token actions.
   - Must include the approval token when advancing a governed step.

2. Activity timeline
   - Renders workflow events returned by the backend.
   - Expected event types include:
     - `agentic_route_selected`
     - `capabilities_shown`
     - `fields_catalog_shown`
     - `checks_proposed`
     - `approval_requested`
     - `customers_evaluated`
     - `message_styles_shown`
     - `messages_drafted`
     - `workflow_completed`

3. Review panel
   - Renders shortlisted customers, checks, recommendations, and drafted messages.
   - Uses `structured_result` rather than parsing the natural-language `message`.

4. Agent route panel
   - Optional reviewer/admin view.
   - Renders `structured_result.agentic_route.intent`, `tool_name`, `extracted_filters`, and `risk_flags`.
   - Helps explain why the agent chose a catalog response, approval continuation, or campaign workflow.

## Future API Adapter

If a REST adapter is added, keep it small:

- `POST /api/v1/workflows`
- `POST /api/v1/workflows/{session_id}/messages`
- `POST /api/v1/workflows/{session_id}/approvals`
- `GET /api/v1/workflows/{session_id}`
- `GET /api/v1/workflows/{session_id}/events`

Each endpoint should call `WorkflowService` and reuse the same Pydantic DTOs.

Approvals should be modeled as token-bound actions. The future UI may render buttons, but the backend should still send prompts containing the active approval token, for example `approve abc12345 INT001 CRD001`.

## References

- AgentCore Runtime overview: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-how-it-works.html
