# Instability Risk Scenarios - Progress Tracker

## Status: Implementation Complete

**Date**: 2026-04-01
**Branch**: features/liem

---

## Implementation Summary

| # | Scenario                  | File                                              | Status |
|---|---------------------------|----------------------------------------------------|--------|
| 0 | Instability Base Class    | `src/scenarios/instability/base_scenario.py`       | Done   |
| 1 | Stop-and-Go Wave          | `src/scenarios/instability/scenario_stop_and_go.py`| Done   |
| 2 | Mixed Speed Fleet         | `src/scenarios/instability/scenario_mixed_speed.py`| Done   |
| 3 | Erratic Speed Fluctuation | `src/scenarios/instability/scenario_erratic.py`    | Done   |
| 4 | Oscillating Speed Limit   | `src/scenarios/instability/scenario_oscillating_limit.py` | Done |
| - | Runner Script             | `src/scenarios/instability/run_all.py`             | Done   |
| - | Plan Document             | `docs/instability/plan.md`                         | Done   |

## Key Design Decision: Proper Instability Metric

The existing `instability_risk()` function in `src/application/risk/instability.py` is broken:
```python
# Always returns 0 because np.std([single_value]) = 0
def instability_risk(speed):
    return np.std([speed]) / (speed + 1e-5) if speed > 0 else 0
```

The `InstabilityBaseScenario` computes a proper Coefficient of Variation (CV) using per-vehicle speeds:
```python
veh_ids = traci.lane.getLastStepVehicleIDs(lane)
speeds = [traci.vehicle.getSpeed(v) for v in veh_ids]
Ri = np.std(speeds) / np.mean(speeds)
```

This properly captures speed variance across vehicles on the same lane.

## Code Reuse Map

| Existing Module | Reused In | Purpose |
|---|---|---|
| `src/physical/sumo_env.py` | `InstabilityBaseScenario.__init__()` | SUMO start/step/close |
| `src/physical/detectors.py` | via `StateSync.sync()` | Lane data extraction |
| `src/twin/state_model.py` | `InstabilityBaseScenario.__init__()` | TrafficState container |
| `src/twin/state_sync.py` | `InstabilityBaseScenario.run()` | Physical -> twin sync |
| `src/twin/feature_extractor.py` | via `StateSync.sync()` | Density computation |
| `src/application/risk/risk_manager.py` | `InstabilityBaseScenario.run()` | Rc, Rs (congestion, spillback) |

## How to Run

```bash
# All scenarios
python -m src.scenarios.instability.run_all

# Single scenario by name
python -m src.scenarios.instability.run_all stopgo
python -m src.scenarios.instability.run_all mixed
python -m src.scenarios.instability.run_all erratic
python -m src.scenarios.instability.run_all oscillating

# List available
python -m src.scenarios.instability.run_all --list
```

## Output

CSV files written to `outputs/scenarios/` with naming pattern:
```
<scenario_name>_<YYYYMMDD_HHMMSS>.csv
```

Columns: step, vehicle_count, avg_instability, max_instability, avg_congestion, max_congestion, unstable_lanes, total_lanes, worst_lane, worst_lane_cv.

## Next Steps

- [ ] Run all scenarios and validate instability thresholds are reached
- [ ] Analyze CSV outputs for before/during/after patterns
- [ ] Compare instability vs congestion metrics (they should behave differently)
- [ ] Consider fixing `src/application/risk/instability.py` to use per-vehicle CV
- [ ] Add visualization (matplotlib plots of Ri over time)
