import "server-only";

import {
  BedrockAgentCoreClient,
  InvokeAgentRuntimeCommand,
  type InvokeAgentRuntimeCommandOutput
} from "@aws-sdk/client-bedrock-agentcore";

import type { AgentResponse } from "@/lib/types";

export type InvokeAgentInput = {
  prompt: string;
  sessionId?: string;
  requestId?: string;
};

export async function invokeAgentCore(input: InvokeAgentInput): Promise<AgentResponse> {
  if (process.env.DASHBOARD_USE_MOCK_AGENT === "true") {
    return mockAgentResponse(input);
  }

  const runtimeArn = process.env.AGENTCORE_RUNTIME_ARN;
  if (!runtimeArn) {
    throw new Error("AGENTCORE_RUNTIME_ARN is not configured.");
  }

  const region = process.env.AWS_REGION || "ap-south-1";
  const client = new BedrockAgentCoreClient({ region });
  const payload = JSON.stringify({
    session_id: input.sessionId,
    request_id: input.requestId,
    prompt: input.prompt
  });
  const command = new InvokeAgentRuntimeCommand({
    agentRuntimeArn: runtimeArn,
    runtimeSessionId: input.sessionId,
    contentType: "application/json",
    accept: "application/json",
    payload: new TextEncoder().encode(payload)
  });
  const output = await client.send(command);
  const body = await agentResponseToText(output.response);
  return JSON.parse(body) as AgentResponse;
}

async function agentResponseToText(
  response: InvokeAgentRuntimeCommandOutput["response"]
): Promise<string> {
  if (!response) {
    return "";
  }
  if (response instanceof Uint8Array) {
    return Buffer.from(response).toString("utf-8");
  }
  const streamLike = response as { transformToString?: () => Promise<string> };
  if (typeof streamLike.transformToString === "function") {
    return streamLike.transformToString();
  }
  if (typeof Blob !== "undefined" && response instanceof Blob) {
    return response.text();
  }
  return String(response);
}

function mockAgentResponse(input: InvokeAgentInput): AgentResponse {
  const sessionId = input.sessionId || "mock-session";
  const approvalCount = (input.prompt.match(/approve/g) ?? []).length;
  if (input.prompt.startsWith("approve")) {
    if (input.prompt.includes("premium_exclusive") || input.prompt.includes("warm_assisted")) {
      return mockDraftApproval(sessionId);
    }
    if (approvalCount >= 1 && input.prompt.includes("finalize")) {
      return mockCompleted(sessionId);
    }
    if (input.prompt.includes("INT") || input.prompt.includes("CRD") || input.prompt.includes("TIM")) {
      return mockShortlist(sessionId);
    }
    if (input.sessionId === "mock-style") {
      return mockDraftApproval(sessionId);
    }
    if (input.sessionId === "mock-drafts") {
      return mockDrafts(sessionId);
    }
    if (input.sessionId === "mock-final") {
      return mockCompleted(sessionId);
    }
    if (input.sessionId === "mock-shortlist") {
      return mockStyle(sessionId);
    }
    if (input.sessionId === "mock-checks") {
      return mockShortlist(sessionId);
    }
    return mockChecks(sessionId);
  }
  return {
    session_id: "mock-checks",
    status: "needs_approval",
    message: "Mock agent selected customers for evaluation.",
    suggested_prompts: ["approve mocktoken"],
    approval_token: "mocktoken",
    events: [
      {
        event_type: "approval_requested",
        message: "Requested approval for customer selection.",
        payload: { step: "customer_selection" }
      }
    ],
    structured_result: {
      workflow_stage: "cohort_selection",
      customer_count: 5,
      selection_summary: input.prompt,
      agentic_route: mockRoute("campaign_workflow", "The user asked to score a CRM cohort.")
    }
  };
}

function mockChecks(sessionId: string): AgentResponse {
  return {
    session_id: "mock-checks",
    status: "needs_approval",
    message: "Mock checks are ready. Run hard filters and selected scoring checks.",
    suggested_prompts: ["approve mocktoken INT001 CRD001 TIM001"],
    approval_token: "mocktoken",
    events: [{ event_type: "checks_proposed", message: "Proposed checks.", payload: {} }],
    structured_result: {
      workflow_stage: "check_selection",
      checks: [],
      agentic_route: mockRoute("approval_continuation", "Approval continued to check selection.")
    }
  };
}

function mockShortlist(sessionId: string): AgentResponse {
  return {
    session_id: "mock-shortlist",
    status: "needs_approval",
    message: "Mock evaluation completed. One eligible account is ready for shortlist approval.",
    suggested_prompts: ["approve mocktoken"],
    approval_token: "mocktoken",
    events: [{ event_type: "customers_evaluated", message: "Evaluated and ranked customers.", payload: {} }],
    structured_result: {
      workflow_stage: "shortlist_review",
      top_customers: [
        {
          customer_id: "CUST0001",
          name: "Aarav Verma",
          score: 84,
          priority: "P1",
          likelihood_pct: 78,
          recommended_channel: "Push Notification",
          offer_amount: 650000,
          next_action: "Relationship manager call plus personalized message.",
          reason_codes: ["Incomplete loan application", "Stable salary credit", "Recent app activity"]
        }
      ],
      excluded_count: 1,
      excluded_customers: [
        {
          customer_id: "CUST0009",
          name: "Meera Rao",
          failed_hard_filters: ["Customer Not on DND"]
        }
      ],
      selected_check_ids: ["INT001", "CRD001", "TIM001"],
      agentic_route: mockRoute("approval_continuation", "Approval turns continue the governed workflow.")
    }
  };
}

function mockStyle(sessionId: string): AgentResponse {
  return {
    session_id: "mock-style",
    status: "needs_approval",
    message: "Choose the outreach style for the approved shortlist.",
    suggested_prompts: ["approve mocktoken warm_assisted"],
    approval_token: "mocktoken",
    events: [{ event_type: "message_styles_shown", message: "Requested style approval.", payload: {} }],
    structured_result: {
      workflow_stage: "message_style",
      styles: [],
      recommended_tone_id: "warm_assisted",
      agentic_route: mockRoute("approval_continuation", "Shortlist accepted.")
    }
  };
}

function mockDraftApproval(sessionId: string): AgentResponse {
  return {
    session_id: "mock-drafts",
    status: "needs_approval",
    message: "Warm assisted style selected. Generate drafts for approved accounts.",
    suggested_prompts: ["approve mocktoken"],
    approval_token: "mocktoken",
    events: [{ event_type: "approval_requested", message: "Requested drafting approval.", payload: {} }],
    structured_result: {
      workflow_stage: "draft_generation",
      tone_id: "warm_assisted",
      agentic_route: mockRoute("approval_continuation", "Message style approved.")
    }
  };
}

function mockDrafts(sessionId: string): AgentResponse {
  return {
    session_id: "mock-final",
    status: "needs_approval",
    message: "Drafted 1 compliant outreach message. Final approval is required.",
    suggested_prompts: ["approve mocktoken"],
    approval_token: "mocktoken",
    events: [{ event_type: "messages_drafted", message: "Drafted personalized outreach messages.", payload: {} }],
    structured_result: {
      workflow_stage: "final_approval",
      drafts: [
        {
          customer_id: "CUST0001",
          tone_id: "warm_assisted",
          template_id: "TPL001",
          channel: "Push Notification",
          subject: "Personal loan offer",
          body: "Hi Aarav, your personal loan request is almost complete. You may be eligible for up to Rs 650,000 with flexible EMI options.",
          cta: "Review offer",
          safety_notes: ["Sensitive inferred triggers were not used directly."],
          source_evidence: ["Incomplete loan application", "Stable salary credit"]
        }
      ],
      agentic_route: mockRoute("approval_continuation", "Draft generation approved.")
    }
  };
}

function mockCompleted(sessionId: string): AgentResponse {
  return {
    session_id: sessionId,
    status: "completed",
    message: "Final outreach package approved.",
    suggested_prompts: [],
    approval_token: null,
    events: [{ event_type: "workflow_completed", message: "Final messages approved.", payload: {} }],
    structured_result: {
      workflow_stage: "completed",
      drafts: [],
      agentic_route: mockRoute("approval_continuation", "Final approval recorded.")
    }
  };
}

function mockRoute(intent: string, rationale: string) {
  return {
    intent,
    tool_name: "run_workflow_prompt",
    rationale,
    extracted_filters: { segment: "premium" },
    risk_flags: []
  };
}
