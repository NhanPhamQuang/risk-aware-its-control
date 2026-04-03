-- ============================================================
-- scenario_runs: metadata for each scenario execution
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS scenario_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_type       VARCHAR(50)  NOT NULL,   -- 'congestion', 'instability', 'spillback'
    scenario_type   VARCHAR(100) NOT NULL,   -- e.g. 'surge', 'incident', 'stopgo', 'junction', ...
    execute_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    run_successfully BOOLEAN     NOT NULL DEFAULT FALSE,
    sumo_log        TEXT,
    app_log         TEXT
);

CREATE INDEX IF NOT EXISTS idx_scenario_runs_risk_type
    ON scenario_runs (risk_type);

CREATE INDEX IF NOT EXISTS idx_scenario_runs_scenario_type
    ON scenario_runs (risk_type, scenario_type);

CREATE INDEX IF NOT EXISTS idx_scenario_runs_execute_at
    ON scenario_runs USING BRIN (execute_at);
