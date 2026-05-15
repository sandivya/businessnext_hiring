"""Application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="BUSINESSNEXT_", extra="ignore")

    database_path: Path = Field(default=ROOT_DIR / "data" / "businessnext.db")
    customers_seed_path: Path = Field(
        default=ROOT_DIR / "data" / "seed" / "fabricated_bank_customers_poc_100.json"
    )
    shortlisting_rules_path: Path = Field(
        default=ROOT_DIR / "data" / "seed" / "personal_loan_shortlisting_rules_ui_ready.json"
    )
    messaging_rules_path: Path = Field(
        default=ROOT_DIR / "data" / "seed" / "personlaised_messaging_rules.json"
    )
    aws_region: str = "ap-south-1"
    bedrock_model_id: str = "openai.gpt-oss-safeguard-120b"
    agent_system_prompt_path: Path = Field(default=ROOT_DIR / "agent.md")
    agent_id: str = "businessnext-personal-loan-agent"
    agent_name: str = "BusinessNext Personal Loan Outreach Agent"
    agent_description: str = (
        "Governed personal-loan campaign agent with HITL approvals, explainable "
        "shortlisting, and safe message drafting."
    )
    bedrock_max_concurrency: int = 3
    model_retry_max_attempts: int = 3
    model_retry_initial_delay_seconds: int = 2
    model_retry_max_delay_seconds: int = 30
    conversation_window_size: int = 20
    conversation_management_per_turn: bool = True
    log_level: str = "INFO"
    use_fake_model: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for app startup paths."""

    return Settings()
