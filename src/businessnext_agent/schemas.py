"""Pydantic contracts shared by AgentCore, workflow logic, and a future frontend."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ResponseStatus(StrEnum):
    COMPLETED = "completed"
    NEEDS_APPROVAL = "needs_approval"
    NEEDS_CLARIFICATION = "needs_clarification"
    ERROR = "error"


class ApprovalStep(StrEnum):
    CUSTOMER_SELECTION = "customer_selection"
    CHECK_SELECTION = "check_selection"
    SHORTLIST_ACCEPTANCE = "shortlist_acceptance"
    MESSAGE_STYLE = "message_style"
    BEDROCK_DRAFTING = "bedrock_drafting"
    FINAL_MESSAGES = "final_messages"


class AgentRequest(BaseModel):
    """Single prompt-only AgentCore invocation input."""

    session_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    prompt: str = ""


class WorkflowEvent(BaseModel):
    """Frontend-ready activity event."""

    event_type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Stable AgentCore output contract."""

    session_id: str
    status: ResponseStatus
    message: str
    suggested_prompts: list[str] = Field(default_factory=list)
    approval_token: str | None = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    structured_result: dict[str, Any] = Field(default_factory=dict)


class RuleOutcome(BaseModel):
    """Result for one evaluated rule."""

    rule_id: str
    display_name: str
    passed: bool
    points: int = 0
    category: str | None = None
    reason: str


class Recommendation(BaseModel):
    """Personal-loan outreach recommendation."""

    product: Literal["personal_loan"] = "personal_loan"
    offer_type: str
    suggested_action: str
    preferred_channel: str | None = None
    amount: float | None = None
    rate_pct: float | None = None
    rationale: list[str] = Field(default_factory=list)


class CustomerEvaluation(BaseModel):
    """Explainable customer scoring result."""

    customer_id: str
    full_name: str
    eligible: bool
    score: int
    priority_band: str
    priority_label: str
    heuristic_likelihood_pct: int
    failed_hard_filters: list[RuleOutcome] = Field(default_factory=list)
    matched_rules: list[RuleOutcome] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    recommendation: Recommendation


class MessageDraft(BaseModel):
    """Final customer outreach draft."""

    customer_id: str
    tone_id: str
    template_id: str
    channel: str
    subject: str | None = None
    body: str
    cta: str
    safety_notes: list[str] = Field(default_factory=list)
    source_evidence: list[str] = Field(default_factory=list)


class SessionState(BaseModel):
    """Persisted conversational workflow state."""

    model_config = ConfigDict(extra="allow")

    session_id: str
    has_seen_capabilities: bool = False
    pending_step: ApprovalStep | None = None
    approval_token: str | None = None
    selected_customer_ids: list[str] = Field(default_factory=list)
    selected_check_ids: list[str] = Field(default_factory=list)
    selection_summary: str = ""
    evaluations: list[CustomerEvaluation] = Field(default_factory=list)
    chosen_tone_id: str | None = None
    message_drafts: list[MessageDraft] = Field(default_factory=list)
    last_prompt: str = ""
