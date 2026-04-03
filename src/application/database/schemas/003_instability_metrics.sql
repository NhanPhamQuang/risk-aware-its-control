-- ============================================================
-- instability_metrics: per-step data from instability scenarios
-- Append-only, optimised for aggregation (SUM, AVG, MAX, MIN)
-- ============================================================
-- CSV columns: step, vehicle_count, avg_instability, max_instability,
--              avg_congestion, max_congestion, unstable_lanes,
--              total_lanes, worst_lane, worst_lane_cv

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
