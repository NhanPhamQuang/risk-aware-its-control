-- ============================================================
-- congestion_metrics: per-step data from congestion scenarios
-- Append-only, optimised for aggregation (SUM, AVG, MAX, MIN)
-- ============================================================
-- CSV columns: step, vehicle_count, avg_congestion, max_congestion,
--              avg_spillback, max_spillback, congested_lanes,
--              total_lanes, worst_lane

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

-- BRIN indexes: ideal for append-only sequential inserts
CREATE INDEX IF NOT EXISTS idx_congestion_metrics_run_brin
    ON congestion_metrics USING BRIN (run_id);

CREATE INDEX IF NOT EXISTS idx_congestion_metrics_step_brin
    ON congestion_metrics USING BRIN (step);
