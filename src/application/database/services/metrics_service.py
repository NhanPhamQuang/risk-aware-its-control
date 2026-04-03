"""Service for bulk-inserting and querying per-step metrics.

Each risk type maps to its own table with typed columns so that native
SQL aggregations (SUM, AVG, MAX, MIN) run directly on indexed data
without JSON extraction overhead.
"""

from __future__ import annotations

import csv
import uuid
from io import StringIO
from pathlib import Path

import psycopg2
import psycopg2.extras

from .connection import get_connection

psycopg2.extras.register_uuid()

# ── Column definitions per risk type ────────────────────────────────
# Order must match the CSV header order produced by each base_scenario.

CONGESTION_COLUMNS = (
    "step", "vehicle_count",
    "avg_congestion", "max_congestion",
    "avg_spillback", "max_spillback",
    "congested_lanes", "total_lanes", "worst_lane",
)

INSTABILITY_COLUMNS = (
    "step", "vehicle_count",
    "avg_instability", "max_instability",
    "avg_congestion", "max_congestion",
    "unstable_lanes", "total_lanes", "worst_lane", "worst_lane_cv",
)

SPILLBACK_COLUMNS = (
    "step", "vehicle_count",
    "avg_spillback", "max_spillback",
    "avg_congestion",
    "total_queue", "max_queue",
    "spillback_lanes", "propagating_lanes", "total_lanes",
    "worst_lane", "worst_lane_queue",
)

RISK_TABLE_MAP = {
    "congestion":  ("congestion_metrics",  CONGESTION_COLUMNS),
    "instability": ("instability_metrics", INSTABILITY_COLUMNS),
    "spillback":   ("spillback_metrics",   SPILLBACK_COLUMNS),
}

# Numeric columns that should be cast from CSV strings
_INT_COLS = {
    "step", "vehicle_count", "congested_lanes", "total_lanes",
    "unstable_lanes", "spillback_lanes", "propagating_lanes",
    "total_queue", "max_queue", "worst_lane_queue",
}
_FLOAT_COLS = {
    "avg_congestion", "max_congestion", "avg_spillback", "max_spillback",
    "avg_instability", "max_instability", "worst_lane_cv",
}


def _cast(col: str, val: str):
    """Convert a raw CSV string to the appropriate Python type."""
    val = val.strip()
    if val == "" or val.lower() == "nan":
        return None
    if col in _INT_COLS:
        return int(float(val))
    if col in _FLOAT_COLS:
        return float(val)
    return val  # worst_lane → kept as str


class MetricsService:
    """Bulk insert and aggregate query service for metrics tables."""

    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self.conn.autocommit = True

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------
    def ensure_tables(self):
        """Create all three metrics tables if they don't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS congestion_metrics (
                    run_id          UUID             NOT NULL REFERENCES scenario_runs(id) ON DELETE CASCADE,
                    step            INT              NOT NULL,
                    vehicle_count   INT,
                    avg_congestion  DOUBLE PRECISION,
                    max_congestion  DOUBLE PRECISION,
                    avg_spillback   DOUBLE PRECISION,
                    max_spillback   DOUBLE PRECISION,
                    congested_lanes INT,
                    total_lanes     INT,
                    worst_lane      VARCHAR(100),
                    PRIMARY KEY (run_id, step)
                );
                CREATE INDEX IF NOT EXISTS idx_congestion_metrics_run_brin
                    ON congestion_metrics USING BRIN (run_id);
                CREATE INDEX IF NOT EXISTS idx_congestion_metrics_step_brin
                    ON congestion_metrics USING BRIN (step);

                CREATE TABLE IF NOT EXISTS instability_metrics (
                    run_id           UUID             NOT NULL REFERENCES scenario_runs(id) ON DELETE CASCADE,
                    step             INT              NOT NULL,
                    vehicle_count    INT,
                    avg_instability  DOUBLE PRECISION,
                    max_instability  DOUBLE PRECISION,
                    avg_congestion   DOUBLE PRECISION,
                    max_congestion   DOUBLE PRECISION,
                    unstable_lanes   INT,
                    total_lanes      INT,
                    worst_lane       VARCHAR(100),
                    worst_lane_cv    DOUBLE PRECISION,
                    PRIMARY KEY (run_id, step)
                );
                CREATE INDEX IF NOT EXISTS idx_instability_metrics_run_brin
                    ON instability_metrics USING BRIN (run_id);
                CREATE INDEX IF NOT EXISTS idx_instability_metrics_step_brin
                    ON instability_metrics USING BRIN (step);

                CREATE TABLE IF NOT EXISTS spillback_metrics (
                    run_id            UUID             NOT NULL REFERENCES scenario_runs(id) ON DELETE CASCADE,
                    step              INT              NOT NULL,
                    vehicle_count     INT,
                    avg_spillback     DOUBLE PRECISION,
                    max_spillback     DOUBLE PRECISION,
                    avg_congestion    DOUBLE PRECISION,
                    total_queue       INT,
                    max_queue         INT,
                    spillback_lanes   INT,
                    propagating_lanes INT,
                    total_lanes       INT,
                    worst_lane        VARCHAR(100),
                    worst_lane_queue  INT,
                    PRIMARY KEY (run_id, step)
                );
                CREATE INDEX IF NOT EXISTS idx_spillback_metrics_run_brin
                    ON spillback_metrics USING BRIN (run_id);
                CREATE INDEX IF NOT EXISTS idx_spillback_metrics_step_brin
                    ON spillback_metrics USING BRIN (step);
            """)

    # ------------------------------------------------------------------
    # Bulk insert
    # ------------------------------------------------------------------
    def insert_from_csv(
        self, run_id: uuid.UUID, risk_type: str, csv_path: str | Path
    ) -> int:
        """Read a CSV file and bulk-insert all rows into the matching table.

        Uses ``COPY … FROM STDIN`` via psycopg2's ``copy_expert`` for
        maximum throughput on append-only inserts.

        Returns the number of rows inserted.
        """
        table, columns = RISK_TABLE_MAP[risk_type]
        all_columns = ("run_id",) + columns

        rows = self._parse_csv(columns, csv_path)
        if not rows:
            return 0

        # Build an in-memory TSV buffer for COPY
        buf = StringIO()
        for row in rows:
            line_parts = [str(run_id)]
            for val in row:
                line_parts.append("\\N" if val is None else str(val))
            buf.write("\t".join(line_parts) + "\n")
        buf.seek(0)

        col_list = ", ".join(all_columns)
        copy_sql = f"COPY {table} ({col_list}) FROM STDIN WITH (FORMAT text, NULL '\\N')"

        with self.conn.cursor() as cur:
            cur.copy_expert(copy_sql, buf)

        return len(rows)

    def insert_rows(
        self,
        run_id: uuid.UUID,
        risk_type: str,
        rows: list[dict],
    ) -> int:
        """Insert rows passed as list of dicts (from in-memory metrics).

        Each dict should have keys matching the CSV column names for the
        given *risk_type*.  Returns the number of rows inserted.
        """
        table, columns = RISK_TABLE_MAP[risk_type]
        all_columns = ("run_id",) + columns
        placeholders = ", ".join(["%s"] * len(all_columns))
        insert_sql = f"INSERT INTO {table} ({', '.join(all_columns)}) VALUES ({placeholders})"

        tuples = []
        for row in rows:
            values = [run_id] + [row.get(c) for c in columns]
            tuples.append(tuple(values))

        with self.conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, insert_sql, tuples, page_size=500)

        return len(tuples)

    # ------------------------------------------------------------------
    # Aggregation queries
    # ------------------------------------------------------------------
    def aggregate(
        self,
        risk_type: str,
        run_id: uuid.UUID | None = None,
        columns: list[str] | None = None,
        agg: str = "AVG",
    ) -> dict:
        """Run an aggregate function across numeric columns of a metrics table.

        Parameters
        ----------
        risk_type : str
            One of 'congestion', 'instability', 'spillback'.
        run_id : UUID, optional
            Scope to a single run.  If *None*, aggregate across all rows.
        columns : list[str], optional
            Specific columns to aggregate.  Defaults to all numeric columns.
        agg : str
            SQL aggregate function: 'AVG', 'SUM', 'MAX', 'MIN', 'COUNT'.

        Returns
        -------
        dict  mapping ``column_name → aggregated_value``.
        """
        agg = agg.upper()
        if agg not in ("AVG", "SUM", "MAX", "MIN", "COUNT"):
            raise ValueError(f"Unsupported aggregate function: {agg}")

        table, all_cols = RISK_TABLE_MAP[risk_type]

        # Default: aggregate all numeric columns
        if columns is None:
            columns = [c for c in all_cols if c in _INT_COLS | _FLOAT_COLS]

        select_parts = [f"{agg}({c}) AS {c}" for c in columns]
        select_sql = ", ".join(select_parts)

        where, params = "", []
        if run_id is not None:
            where = "WHERE run_id = %s"
            params.append(run_id)

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT {select_sql} FROM {table} {where}", params)
            return dict(cur.fetchone())

    def get_metrics(
        self,
        risk_type: str,
        run_id: uuid.UUID,
        step_from: int | None = None,
        step_to: int | None = None,
    ) -> list[dict]:
        """Fetch raw metric rows for a run, optionally filtered by step range."""
        table, _ = RISK_TABLE_MAP[risk_type]

        clauses = ["run_id = %s"]
        params: list = [run_id]

        if step_from is not None:
            clauses.append("step >= %s")
            params.append(step_from)
        if step_to is not None:
            clauses.append("step <= %s")
            params.append(step_to)

        where = "WHERE " + " AND ".join(clauses)

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM {table} {where} ORDER BY step", params
            )
            return cur.fetchall()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_csv(columns: tuple, csv_path: str | Path) -> list[tuple]:
        """Parse a scenario CSV into a list of typed tuples."""
        rows = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                row = tuple(_cast(c, raw[c]) for c in columns)
                rows.append(row)
        return rows

    # ------------------------------------------------------------------
    def close(self):
        self.conn.close()
