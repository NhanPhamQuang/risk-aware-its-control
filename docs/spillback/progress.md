# Spillback Risk Scenarios - Progress Tracker

## Status: Implementation Complete

**Date**: 2026-04-02
**Branch**: features/liem

---

## Implementation Summary

| # | Scenario                      | File                                                    | Status |
|---|-------------------------------|---------------------------------------------------------|--------|
| 0 | Spillback Base Class          | `src/scenarios/spillback/base_scenario.py`              | Done   |
| 1 | Junction Blockage             | `src/scenarios/spillback/scenario_junction_blockage.py`  | Done   |
| 2 | Downstream Capacity Reduction | `src/scenarios/spillback/scenario_downstream_reduction.py`| Done  |
| 3 | Demand Flood Spillback        | `src/scenarios/spillback/scenario_demand_flood.py`       | Done   |
| 4 | Cascading Spillback           | `src/scenarios/spillback/scenario_cascading_spillback.py` | Done  |
| - | Runner Script                 | `src/scenarios/spillback/run_all.py`                     | Done   |
| - | Plan Document                 | `docs/spillback/plan.md`                                 | Done   |

## Key Design Decisions

### Spillback vs Congestion
Spillback is specifically about **queue propagation across junctions**, not just high density on a single lane. The `SpillbackBaseScenario` tracks this via:
- `propagating_lanes`: lanes where BOTH the lane and its downstream lane have queues
- `total_queue`: network-wide halted vehicle count (global impact indicator)

### Network Topology Awareness
All scenarios target **Junction 2** (the central 4-way hub) because:
- It's the only junction where multiple routes converge
- Blocking its exits causes maximum upstream impact
- Spillback propagates outward to all 4 boundary junctions

### Enhanced Metric: Queue Propagation Detection
```python
# Check if downstream lanes also have queues
links = traci.lane.getLinks(lane)
for link in links:
    next_lane = link[0]
    if next_lane in self.state.queue and self.state.queue[next_lane] > 0:
        propagating = True
```

## Code Reuse Map

| Existing Module | Reused In | Purpose |
|---|---|---|
| `src/physical/sumo_env.py` | `SpillbackBaseScenario.__init__()` | SUMO start/step/close |
| `src/physical/detectors.py` | via `StateSync.sync()` | Halt count extraction |
| `src/twin/state_model.py` | `SpillbackBaseScenario.__init__()` | TrafficState (queue data) |
| `src/twin/state_sync.py` | `SpillbackBaseScenario.run()` | Physical -> twin sync |
| `src/application/risk/risk_manager.py` | `SpillbackBaseScenario.run()` | Rs = queue / lane_length |
| `src/application/risk/spillback.py` | via `RiskManager.compute()` | Core spillback formula |

## How to Run

```bash
python -m src.scenarios.spillback.run_all               # all
python -m src.scenarios.spillback.run_all junction       # by name
python -m src.scenarios.spillback.run_all --list         # list available
```

## Output

CSV files written to `outputs/scenarios/` with columns: step, vehicle_count, avg_spillback, max_spillback, avg_congestion, total_queue, max_queue, spillback_lanes, propagating_lanes, total_lanes, worst_lane, worst_lane_queue.

## Next Steps

- [ ] Run all scenarios and validate spillback thresholds
- [ ] Verify propagating_lanes metric detects cross-junction spillback
- [ ] Compare recovery time across scenarios (spillback recovers slower than congestion)
- [ ] Add visualization of queue propagation over time
- [ ] Consider updating spillback_risk() lane_length parameter to match actual lane capacity
