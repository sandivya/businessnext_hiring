"""SQLite persistence and seed ingestion."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from businessnext_agent.config import Settings
from businessnext_agent.schemas import SessionState, WorkflowEvent

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SQLiteStore:
    """Small repository layer that can later be swapped for PostgreSQL or DynamoDB."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        self._connection.close()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                name TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rules (
                name TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self._connection.commit()

    def seed_from_files(self, settings: Settings) -> None:
        """Load seed JSON once; repeated calls are idempotent."""

        if self.customer_count() > 0:
            logger.debug("Skipping seed load because customers already exist")
            return
        logger.info("Seeding SQLite store from configured JSON files")
        customer_root = json.loads(settings.customers_seed_path.read_text(encoding="utf-8"))
        shortlisting = json.loads(settings.shortlisting_rules_path.read_text(encoding="utf-8"))
        messaging = json.loads(settings.messaging_rules_path.read_text(encoding="utf-8"))
        self._connection.execute(
            "INSERT OR REPLACE INTO metadata(name, payload) VALUES (?, ?)",
            ("customers", json.dumps(customer_root["metadata"])),
        )
        for customer in customer_root["customers"]:
            self._connection.execute(
                "INSERT OR REPLACE INTO customers(customer_id, payload) VALUES (?, ?)",
                (customer["customer_id"], json.dumps(customer)),
            )
        self._connection.execute(
            "INSERT OR REPLACE INTO rules(name, payload) VALUES (?, ?)",
            ("shortlisting", json.dumps(shortlisting)),
        )
        self._connection.execute(
            "INSERT OR REPLACE INTO rules(name, payload) VALUES (?, ?)",
            ("messaging", json.dumps(messaging)),
        )
        self._connection.commit()
        logger.info("Seeded %s customers into SQLite", len(customer_root["customers"]))

    def customer_count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS count FROM customers").fetchone()
        return int(row["count"])

    def list_customers(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT payload FROM customers ORDER BY customer_id"
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT payload FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        return None if row is None else json.loads(row["payload"])

    def get_metadata(self, name: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT payload FROM metadata WHERE name = ?", (name,)
        ).fetchone()
        return {} if row is None else json.loads(row["payload"])

    def get_rules(self, name: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT payload FROM rules WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            msg = f"Rules not loaded: {name}"
            raise ValueError(msg)
        return json.loads(row["payload"])

    def new_session(self) -> SessionState:
        session_id = str(uuid.uuid4())
        state = SessionState(session_id=session_id)
        self.save_session(state)
        return state

    def get_session(self, session_id: str | None) -> SessionState:
        if not session_id:
            return self.new_session()
        row = self._connection.execute(
            "SELECT state FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return SessionState(session_id=session_id)
        return SessionState.model_validate_json(row["state"])

    def save_session(self, state: SessionState) -> None:
        # Persist the full state so AgentCore and a future frontend can resume the same workflow.
        now = _now_iso()
        payload = state.model_dump_json()
        self._connection.execute(
            """
            INSERT INTO sessions(session_id, state, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id)
            DO UPDATE SET state = excluded.state, updated_at = excluded.updated_at
            """,
            (state.session_id, payload, now, now),
        )
        self._connection.commit()

    def add_event(self, session_id: str, event: WorkflowEvent) -> WorkflowEvent:
        logger.debug("Recording workflow event %s for session %s", event.event_type, session_id)
        self._connection.execute(
            "INSERT INTO events(session_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
            (session_id, event.event_type, event.model_dump_json(), _now_iso()),
        )
        self._connection.commit()
        return event

    def list_events(self, session_id: str) -> list[WorkflowEvent]:
        rows = self._connection.execute(
            "SELECT payload FROM events WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
        return [WorkflowEvent.model_validate_json(row["payload"]) for row in rows]
