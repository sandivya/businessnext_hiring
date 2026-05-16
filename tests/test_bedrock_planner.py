"""Tests for LLM-backed planning."""

from __future__ import annotations

import json

import pytest

from businessnext_agent.orchestration.bedrock_planner import BedrockPlanner
from businessnext_agent.schemas import AgentRequest


class FakeBedrockModel:
    """Fake model for testing planning."""

    def __init__(self, response_dict: dict | None = None, fail: bool = False) -> None:
        self.response_dict = response_dict
        self.fail = fail

    def draft(self, prompt: str, fallback: str) -> str:
        if self.fail:
            raise RuntimeError("Model unavailable")
        if self.response_dict:
            return json.dumps(self.response_dict)
        return fallback


def test_bedrock_planner_produces_valid_plan() -> None:
    model_response = {
        "intent": "campaign_workflow",
        "tool_name": "run_workflow_prompt",
        "prompt": "Find premium customers",
        "rationale": "User is asking for campaign execution.",
        "extracted_filters": {"segment": "premium"},
    }
    model = FakeBedrockModel(response_dict=model_response)
    planner = BedrockPlanner(model)

    request = AgentRequest(prompt="Find premium customers")
    plan = planner.plan(request)

    assert plan.intent == "campaign_workflow"
    assert plan.tool_name == "run_workflow_prompt"
    assert plan.extracted_filters["segment"] == "premium"


def test_bedrock_planner_falls_back_on_invalid_json() -> None:
    model = FakeBedrockModel(response_dict=None, fail=False)
    model.response_dict = "not json"
    planner = BedrockPlanner(model)

    request = AgentRequest(prompt="help")
    with pytest.raises((json.JSONDecodeError, ValueError)):
        planner.plan(request)


def test_bedrock_planner_falls_back_on_model_failure() -> None:
    model = FakeBedrockModel(fail=True)
    planner = BedrockPlanner(model)

    request = AgentRequest(prompt="help")
    with pytest.raises(RuntimeError):
        planner.plan(request)


def test_bedrock_planner_validates_schema() -> None:
    model_response = {
        "intent": "invalid_intent",
        "tool_name": "show_capabilities",
        "prompt": "test",
        "rationale": "test",
    }
    model = FakeBedrockModel(response_dict=model_response)
    planner = BedrockPlanner(model)

    request = AgentRequest(prompt="help")
    with pytest.raises(ValueError):
        planner.plan(request)


def test_bedrock_planner_system_prompt_includes_routing_table() -> None:
    planner = BedrockPlanner(FakeBedrockModel())
    system_prompt = planner._system_prompt()

    assert "capability_discovery" in system_prompt
    assert "workflow_reset" in system_prompt
    assert "campaign_workflow" in system_prompt
    assert "show_capabilities" in system_prompt



