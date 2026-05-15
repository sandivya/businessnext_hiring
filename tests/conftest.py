from __future__ import annotations

from collections.abc import Iterator

import pytest

from businessnext_agent.application.workflow import WorkflowService
from businessnext_agent.config import ROOT_DIR, Settings
from businessnext_agent.runtime import build_service


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "test.db",
        customers_seed_path=ROOT_DIR / "data" / "seed" / "fabricated_bank_customers_poc_100.json",
        shortlisting_rules_path=ROOT_DIR
        / "data"
        / "seed"
        / "personal_loan_shortlisting_rules_ui_ready.json",
        messaging_rules_path=ROOT_DIR / "data" / "seed" / "personlaised_messaging_rules.json",
        use_fake_model=True,
    )


@pytest.fixture
def service(settings: Settings) -> Iterator[WorkflowService]:
    active_service = build_service(settings)
    yield active_service
    active_service.store.close()
