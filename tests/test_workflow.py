from __future__ import annotations

from businessnext_agent.schemas import AgentRequest, ApprovalStep, ResponseStatus, SessionState


def approve_prompt(response) -> str:
    return f"approve {response.approval_token}"


def test_help_catalogs_and_missing_field_guidance(service) -> None:
    help_response = service.handle(AgentRequest(prompt="help"))
    assert help_response.status == ResponseStatus.COMPLETED
    assert help_response.events[0].event_type == "capabilities_shown"

    fields = service.handle(
        AgentRequest(
            session_id=help_response.session_id,
            prompt="show fields for credit_profile.nonexistent",
        )
    )
    assert fields.status == ResponseStatus.COMPLETED
    assert fields.structured_result["unavailable_fields"] == ["credit_profile.nonexistent"]
    assert service._requested_missing_fields("find high-value personal-loan customers.") == []
    missing_during_selection = service.handle(
        AgentRequest(prompt="Find premium customers using credit_profile.nonexistent")
    )
    assert missing_during_selection.status == ResponseStatus.NEEDS_APPROVAL
    assert "credit_profile.nonexistent" in missing_during_selection.message

    checks = service.handle(AgentRequest(session_id=help_response.session_id, prompt="show checks"))
    assert checks.structured_result["checks"]

    styles = service.handle(
        AgentRequest(session_id=help_response.session_id, prompt="show message formats")
    )
    assert styles.structured_result["styles"]


def test_full_guided_workflow_with_approvals(service) -> None:
    start = service.handle(
        AgentRequest(prompt="Find high-value customers likely to convert this month")
    )
    assert start.status == ResponseStatus.NEEDS_APPROVAL
    assert 0 < start.structured_result["customer_count"] < 100

    reminder = service.handle(AgentRequest(session_id=start.session_id, prompt="what next?"))
    assert reminder.status == ResponseStatus.NEEDS_APPROVAL
    assert reminder.structured_result["pending_step"] == ApprovalStep.CUSTOMER_SELECTION

    loose_approval = service.handle(AgentRequest(session_id=start.session_id, prompt="yes"))
    assert loose_approval.status == ResponseStatus.NEEDS_APPROVAL

    checks = service.handle(AgentRequest(session_id=start.session_id, prompt=approve_prompt(start)))
    assert checks.status == ResponseStatus.NEEDS_APPROVAL
    assert checks.events[0].event_type == "checks_proposed"

    shortlist = service.handle(
        AgentRequest(
            session_id=start.session_id,
            prompt=f"{approve_prompt(checks)} INT001 CRD001",
        )
    )
    assert shortlist.status == ResponseStatus.NEEDS_APPROVAL
    assert shortlist.events[0].event_type == "customers_evaluated"
    assert shortlist.structured_result["top_customers"]
    assert shortlist.structured_result["evaluations"]
    assert shortlist.structured_result["selected_check_ids"] == ["INT001", "CRD001"]

    style = service.handle(
        AgentRequest(session_id=start.session_id, prompt=approve_prompt(shortlist))
    )
    assert style.status == ResponseStatus.NEEDS_APPROVAL
    assert style.structured_result["recommended_tone_id"] == "warm_assisted"

    style_reminder = service.handle(
        AgentRequest(session_id=start.session_id, prompt="premium_exclusive")
    )
    assert style_reminder.status == ResponseStatus.NEEDS_APPROVAL
    assert style_reminder.structured_result["pending_step"] == ApprovalStep.MESSAGE_STYLE

    draft_approval = service.handle(
        AgentRequest(
            session_id=start.session_id, prompt=f"{approve_prompt(style)} premium_exclusive"
        )
    )
    assert draft_approval.status == ResponseStatus.NEEDS_APPROVAL
    assert draft_approval.structured_result["tone_id"] == "premium_exclusive"

    drafts = service.handle(
        AgentRequest(session_id=start.session_id, prompt=approve_prompt(draft_approval))
    )
    assert drafts.status == ResponseStatus.NEEDS_APPROVAL
    assert drafts.structured_result["drafts"]

    completed = service.handle(
        AgentRequest(session_id=start.session_id, prompt=approve_prompt(drafts))
    )
    assert completed.status == ResponseStatus.COMPLETED
    assert completed.events[0].event_type == "workflow_completed"


def test_selection_helpers(service) -> None:
    premium_ids = service._select_customers("premium customers")
    preferred_ids = service._select_customers("preferred customers")
    both_ids = service._select_customers("premium preferred customers")
    mumbai_ids = service._select_customers("premium customers in mumbai with bureau score 740")
    salaried_ids = service._select_customers("salaried customers")
    no_match_ids = service._select_customers("customers with bureau score 999999")
    assert premium_ids
    assert preferred_ids
    assert isinstance(both_ids, list)
    assert isinstance(mumbai_ids, list)
    assert salaried_ids
    assert no_match_ids == []
    assert service._extract_tone("please use crisp digital") == "crisp_digital"
    assert service._extract_tone("unknown style") is None
    assert service._select_customers("evaluate CUST0001 and cust0002") == [
        "CUST0001",
        "CUST0002",
    ]
    assert service._extract_customer_ids("CUST0001 CUST0001 CUST0003") == [
        "CUST0001",
        "CUST0003",
    ]
    assert service._requested_employment("salaried and self-employed customers") == {
        "salaried",
        "self employed",
    }
    assert service._threshold_after("bureau score above 760", ["bureau score"]) == 760
    assert service._selection_summary("premium customers in mumbai", premium_ids)


def test_no_customer_match_needs_clarification(service) -> None:
    response = service.handle(AgentRequest(prompt="customers with bureau score 999999"))
    assert response.status == ResponseStatus.NEEDS_CLARIFICATION


def test_empty_shortlist_and_service_helpers(service) -> None:
    state = SessionState(
        session_id="empty-shortlist",
        selected_customer_ids=["missing"],
        selected_check_ids=["INT001"],
    )
    response = service._after_check_selection(state)
    assert response.status == ResponseStatus.NEEDS_CLARIFICATION
    assert response.structured_result["top_customers"] == []
    assert service.strands_tools()
    service.close()
