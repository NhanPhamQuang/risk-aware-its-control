"""Service for managing scenario_runs records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import psycopg2.extras

from .connection import get_connection

# Register the UUID adapter so psycopg2 handles uuid.UUID natively
psycopg2.extras.register_uuid()


class ScenarioRunService:
    """CRUD operations on the ``scenario_runs`` table."""

    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self.conn.autocommit = True

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------
    def ensure_table(self):
        """Create the scenario_runs table if it doesn't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS "pgcrypto";

                CREATE TABLE IF NOT EXISTS scenario_runs (
                    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    risk_type        VARCHAR(50)  NOT NULL,
                    scenario_type    VARCHAR(100) NOT NULL,
                    execute_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    finished_at      TIMESTAMPTZ,
                    run_successfully BOOLEAN      NOT NULL DEFAULT FALSE,
                    sumo_log         TEXT,
                    app_log          TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_scenario_runs_risk_type
                    ON scenario_runs (risk_type);
                CREATE INDEX IF NOT EXISTS idx_scenario_runs_scenario_type
                    ON scenario_runs (risk_type, scenario_type);
                CREATE INDEX IF NOT EXISTS idx_scenario_runs_execute_at
                    ON scenario_runs USING BRIN (execute_at);
            """)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def start_run(self, risk_type: str, scenario_type: str) -> uuid.UUID:
        """Insert a new run row and return its UUID.

        ``execute_at`` is set to NOW() by the database.
        """
        run_id = uuid.uuid4()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scenario_runs (id, risk_type, scenario_type, execute_at)
                VALUES (%s, %s, %s, %s)
                """,
                (run_id, risk_type, scenario_type, datetime.now(timezone.utc)),
            )
        return run_id

    def finish_run(
        self,
        run_id: uuid.UUID,
        success: bool,
        sumo_log: str | None = None,
        app_log: str | None = None,
    ):
        """Mark a run as finished, storing success flag and optional logs."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE scenario_runs
                SET finished_at       = %s,
                    run_successfully  = %s,
                    sumo_log          = %s,
                    app_log           = %s
                WHERE id = %s
                """,
                (datetime.now(timezone.utc), success, sumo_log, app_log, run_id),
            )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_run(self, run_id: uuid.UUID) -> dict | None:
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM scenario_runs WHERE id = %s", (run_id,))
            return cur.fetchone()

    def list_runs(
        self,
        risk_type: str | None = None,
        scenario_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        clauses, params = [], []
        if risk_type:
            clauses.append("risk_type = %s")
            params.append(risk_type)
        if scenario_type:
            clauses.append("scenario_type = %s")
            params.append(scenario_type)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM scenario_runs {where} ORDER BY execute_at DESC LIMIT %s",
                params,
            )
            return cur.fetchall()

    # ------------------------------------------------------------------
    def close(self):
        self.conn.close()
