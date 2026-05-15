"""Bedrock AgentCore entrypoint."""

from __future__ import annotations

from typing import Any

from businessnext_agent.runtime import invoke

try:  # pragma: no cover - exercised when AgentCore package is installed at runtime
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
except ImportError:  # pragma: no cover - local fallback for minimal environments
    BedrockAgentCoreApp = None


def _with_agentcore_context(payload: dict[str, Any], context: Any | None) -> dict[str, Any]:
    """Copy AgentCore context IDs into the payload for logs when available."""

    if context is None:
        return payload
    enriched = dict(payload)
    for payload_key, context_key in {
        "session_id": "session_id",
        "request_id": "request_id",
        "trace_id": "trace_id",
    }.items():
        value = getattr(context, context_key, None)
        if value and not enriched.get(payload_key):
            enriched[payload_key] = value
    return enriched


if BedrockAgentCoreApp is not None:  # pragma: no cover - runtime wrapper
    app = BedrockAgentCoreApp()

    @app.entrypoint
    def agent_invocation(
        payload: dict[str, Any],
        context: Any | None = None,
    ) -> dict[str, Any]:
        return invoke(_with_agentcore_context(payload, context))

    if __name__ == "__main__":
        app.run()
else:
    app = None

    def agent_invocation(payload: dict[str, Any]) -> dict[str, Any]:
        return invoke(payload)
