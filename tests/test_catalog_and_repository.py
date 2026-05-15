from __future__ import annotations

import pytest

from businessnext_agent.config import get_settings
from businessnext_agent.domain.catalog import (
    available_field_names,
    capability_message,
    check_catalog,
    field_catalog,
    message_style_catalog,
)
from businessnext_agent.infrastructure.repository import SQLiteStore
from businessnext_agent.schemas import SessionState, WorkflowEvent


def test_catalogs_and_settings(service) -> None:
    assert "personal-loan outreach workflow" in capability_message()
    assert "Customer profile" in field_catalog()
    assert "full_name" in available_field_names()
    assert len(check_catalog(service.store.get_rules("shortlisting"))) == 33
    styles = message_style_catalog(service.store.get_rules("messaging"))
    assert {style["tone_id"] for style in styles} >= {"warm_assisted", "premium_exclusive"}
    assert get_settings().aws_region == "ap-south-1"


def test_repository_seed_and_session_lifecycle(settings) -> None:
    store = SQLiteStore(settings.database_path)
    try:
        store.seed_from_files(settings)
        store.seed_from_files(settings)
        assert store.customer_count() == 100
        first = store.get_customer("CUST0001")
        assert first is not None
        assert first["customer_id"] == "CUST0001"
        assert store.get_customer("missing") is None
        assert store.get_metadata("customers")["record_count"] == 100
        with pytest.raises(ValueError, match="Rules not loaded"):
            store.get_rules("missing")
        state = store.new_session()
        state.has_seen_capabilities = True
        store.save_session(state)
        loaded = store.get_session(state.session_id)
        assert loaded.has_seen_capabilities is True
        explicit = store.get_session("manual-session")
        assert explicit == SessionState(session_id="manual-session")
        event = WorkflowEvent(event_type="unit", message="Unit event", payload={"ok": True})
        store.add_event(state.session_id, event)
        assert store.list_events(state.session_id)[0].payload == {"ok": True}
    finally:
        store.close()
