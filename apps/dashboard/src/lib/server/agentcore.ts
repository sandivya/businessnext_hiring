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
  if (input.prompt.startsWith("approve")) {
    return {
      session_id: sessionId,
      status: "needs_approval",
      message: "Mock evaluation completed. Approve the shortlist to continue.",
      suggested_prompts: ["approve mocktoken"],
      approval_token: "mocktoken",
      events: [
        {
          event_type: "customers_evaluated",
          message: "Evaluated and ranked customers.",
          payload: { evaluation_count: 2 }
        }
      ],
      structured_result: {
        evaluations: [
          {
            customer_id: "CUST0001",
            full_name: "Aarav Verma",
            eligible: true,
            score: 84,
            priority_band: "P1",
            priority_label: "Priority 1",
            heuristic_likelihood_pct: 78,
            failed_hard_filters: [],
            matched_rules: [],
            missing_fields: [],
            recommendation: {
              product: "personal_loan",
              offer_type: "pre_approved",
              suggested_action: "Relationship manager call plus personalized message.",
              preferred_channel: "Push Notification",
              amount: 650000,
              rate_pct: 11.2,
              rationale: ["Strong intent", "High relationship value"]
            }
          }
        ],
        top_customers: [
          {
            customer_id: "CUST0001",
            name: "Aarav Verma",
            score: 84,
            priority: "P1",
            likelihood_pct: 78
          }
        ]
      }
    };
  }
  return {
    session_id: sessionId,
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
    structured_result: { customer_count: 5, selection_summary: input.prompt }
  };
}
