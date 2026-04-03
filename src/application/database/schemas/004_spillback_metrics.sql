-- ============================================================
-- spillback_metrics: per-step data from spillback scenarios
-- Append-only, optimised for aggregation (SUM, AVG, MAX, MIN)
-- ============================================================
-- CSV columns: step, vehicle_count, avg_spillback, max_spillback,
--              avg_congestion, total_queue, max_queue,
--              spillback_lanes, propagating_lanes, total_lanes,
--              worst_lane, worst_lane_queue

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
