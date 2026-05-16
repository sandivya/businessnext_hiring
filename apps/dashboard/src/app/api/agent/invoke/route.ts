import { randomUUID } from "node:crypto";

import { NextResponse } from "next/server";

import { invokeAgentCore } from "@/lib/server/agentcore";

type InvokeBody = {
  prompt?: unknown;
  sessionId?: unknown;
};

export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as InvokeBody;
    const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
    if (!prompt) {
      return NextResponse.json({ error: "Prompt is required." }, { status: 400 });
    }
    const sessionId = typeof body.sessionId === "string" ? body.sessionId : undefined;
    const response = await invokeAgentCore({
      prompt,
      sessionId,
      requestId: randomUUID()
    });
    return NextResponse.json(response);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Agent invocation failed.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
