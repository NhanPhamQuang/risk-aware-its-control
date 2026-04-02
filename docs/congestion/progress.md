# Congestion Risk Scenarios - Progress Tracker

## Status: Implementation Complete

**Date**: 2026-04-01
**Branch**: features/liem

---

## Implementation Summary

| # | Scenario                 | File                                  | Status      |
|---|--------------------------|---------------------------------------|-------------|
| 0 | Base Scenario Class      | `src/scenarios/congestion/base_scenario.py`      | Done        |
| 1 | Demand Surge             | `src/scenarios/congestion/scenario_demand_surge.py` | Done     |
| 2 | Incident / Lane Blockage | `src/scenarios/congestion/scenario_incident.py`  | Done        |
| 3 | Bottleneck (Speed Reduction) | `src/scenarios/congestion/scenario_bottleneck.py` | Done   |
| 4 | Cascading Congestion     | `src/scenarios/congestion/scenario_cascading.py` | Done        |
| - | Runner Script            | `src/scenarios/congestion/run_all.py`            | Done        |
| - | Plan Document            | `docs/congestion/plan.md`             | Done        |

## Files Created

### Scenario Infrastructure
- `src/scenarios/base_scenario.py` - Base class with shared simulation loop, metrics collection, CSV export, and summary reporting. Reuses: `SumoEnv`, `StateSync`, `TrafficState`, `RiskManager`.
- `src/scenarios/run_all.py` - CLI runner for executing one or all scenarios.
- `src/scenarios/__init__.py` - Package exports for all scenario classes.

### Scenario Implementations
- `src/scenarios/scenario_demand_surge.py` - Injects 8 vehicles every 10 steps during step 100-800. Uses `traci.vehicle.add()` and `traci.route.add()`.
- `src/scenarios/scenario_incident.py` - Stops 3 vehicles on critical lanes during step 200-800. Uses `traci.vehicle.setSpeed(veh, 0)`.
- `src/scenarios/scenario_bottleneck.py` - Reduces lane speed to 2 m/s during step 150-900. Uses `traci.lane.setMaxSpeed()`.
- `src/scenarios/scenario_cascading.py` - Combines all three: surge (step 100-1200) + incident (step 300-900) + bottleneck (step 400-1000).

### Documentation
- `docs/congestion/plan.md` - Full plan with scenario designs, architecture, risk thresholds, and validation criteria.
- `docs/congestion/progress.md` - This file.

## Code Reuse Map

| Existing Module | Reused In | Purpose |
|---|---|---|
| `src/physical/sumo_env.py` | `BaseScenario.__init__()` | SUMO start/step/close |
| `src/physical/detectors.py` | via `StateSync.sync()` | Lane data extraction |
| `src/twin/state_model.py` | `BaseScenario.__init__()` | TrafficState container |
| `src/twin/state_sync.py` | `BaseScenario.run()` | Physical -> twin sync |
| `src/twin/feature_extractor.py` | via `StateSync.sync()` | Density computation |
| `src/application/risk/risk_manager.py` | `BaseScenario.run()` | Rc, Ri, Rs computation |
| `src/application/risk/congestion.py` | via `RiskManager.compute()` | `density / jam_density` |
| `src/application/risk/spillback.py` | via `RiskManager.compute()` | `queue / lane_length` |
| `src/application/risk/instability.py` | via `RiskManager.compute()` | Speed variance |

## Network Notes

- The current network has **no traffic lights** (all junctions are priority-type).
- Original "Signal Failure" scenario was replaced with "Cascading Congestion" (combined stress test) since there are no TLS to fail.
- All 8 lanes are ~100m long with max speed 27.78 m/s (100 km/h).
- To reach jam density (`Rc = 1.0`) on a 100m lane: need ~20 vehicles simultaneously.

## How to Run

```bash
# All scenarios
python -m src.scenarios.congestion.run_all

# Single scenario
python -m src.scenarios.congestion.run_all 1    # demand surge only
python -m src.scenarios.congestion.run_all 4    # cascading only

# Direct execution
python -m src.scenarios.congestion.scenario_demand_surge
```

## Output

CSV files are written to `outputs/scenarios/` with naming pattern:
```
<scenario_name>_<YYYYMMDD_HHMMSS>.csv
```

Each CSV contains per-step metrics: step, vehicle_count, avg_congestion, max_congestion, avg_spillback, max_spillback, congested_lanes, total_lanes, worst_lane.

## Next Steps

- [ ] Run all scenarios and validate congestion risk thresholds are reached
- [ ] Analyze CSV outputs for before/during/after patterns
- [ ] Add visualization (matplotlib plots of Rc over time)
- [ ] Compare scenario severity and recovery characteristics
- [ ] Integrate with DBLogger for persistent storage
- [ ] Consider adding traffic light network for signal failure scenario
