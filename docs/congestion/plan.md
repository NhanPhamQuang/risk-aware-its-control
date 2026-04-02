# Congestion Risk Scenario Plan

## 1. Objective

Design and implement reproducible simulation scenarios that trigger **congestion risk** in the Risk-Aware ITS Digital Twin system. Each scenario uses SUMO + TraCI to create specific traffic conditions where `congestion_risk(density) = density / jam_density` exceeds safe thresholds, validating the system's risk detection capabilities.

## 2. Background: Congestion Risk

### Definition
Congestion risk quantifies how close a lane's vehicle density is to the jam density threshold. When density approaches or exceeds `jam_density = 0.2 veh/m`, traffic flow degrades into stop-and-go conditions.

### Formula (from `src/application/risk/congestion.py`)
```
Rc = density / jam_density
```
Where:
- `density = vehicle_count / lane_length` (from `feature_extractor.py`)
- `jam_density = 0.2 veh/m` (default threshold)

### Risk Levels
| Level     | Rc Range | Meaning                    |
|-----------|----------|----------------------------|
| Low       | 0.0-0.3  | Free flow                  |
| Medium    | 0.3-0.6  | Approaching capacity       |
| High      | 0.6-0.8  | Near breakdown             |
| Critical  | > 0.8    | Jammed / gridlock          |

## 3. Network Characteristics

The SUMO network (`network/map.net.xml`) has:
- **8 edges**: 100#0, 100#1, 101#0, 101#1 and their reverse directions
- **8 lanes**: 1 lane per edge, ~100m each, max speed 27.78 m/s (100 km/h)
- **5 junctions**: All priority-type (yield-based, no traffic lights)
- **Baseline demand**: 1 vehicle/second for 3600 seconds (`demand/routes.rou.xml`)

To reach `Rc = 1.0` on a 100m lane: need `100m * 0.2 veh/m = 20 vehicles` simultaneously.

## 4. Scenario Designs

### Scenario 1: Demand Surge
**File**: `src/scenarios/congestion/scenario_demand_surge.py`

**Concept**: Simulates rush-hour or event dispersal by injecting bursts of vehicles that overwhelm network capacity.

**Mechanism**:
- Every 10 simulation steps, inject 8 vehicles with random routes
- Surge window: step 100 to step 800
- Total injected: ~560 extra vehicles on top of baseline demand

**Expected congestion pattern**:
```
Step 0-100:    Normal flow (Rc < 0.3)
Step 100-400:  Building congestion (Rc 0.3-0.6)
Step 400-800:  Peak congestion (Rc > 0.8)
Step 800+:     Recovery as surge stops (Rc decreasing)
```

**TraCI APIs used**:
- `traci.route.add()` - create dynamic routes
- `traci.vehicle.add()` - inject vehicles
- `traci.lane.getLinks()` - find valid downstream edges

---

### Scenario 2: Incident / Lane Blockage
**File**: `src/scenarios/congestion/scenario_incident.py`

**Concept**: Simulates an accident or breakdown by forcing vehicles to stop on critical lanes, creating a physical bottleneck.

**Mechanism**:
- At step 200, find and stop 3 vehicles on lanes `100#0_0` and `-100#1_0`
- Stopped vehicles block the lane for 600 steps (until step 800)
- Upstream vehicles queue behind the blockage

**Expected congestion pattern**:
```
Step 0-200:    Normal flow
Step 200-250:  Sudden density spike on blocked lanes
Step 250-800:  Sustained high Rc + spillback propagation upstream
Step 800+:     Incident cleared, gradual recovery
```

**TraCI APIs used**:
- `traci.vehicle.setSpeed(veh, 0)` - force vehicle to stop
- `traci.vehicle.setColor()` - visual marker for blocked vehicles
- `traci.lane.getLastStepVehicleIDs()` - find vehicles on target lanes

---

### Scenario 3: Bottleneck via Speed Reduction
**File**: `src/scenarios/congestion/scenario_bottleneck.py`

**Concept**: Simulates road works or construction by drastically reducing the speed limit on key lanes, creating a capacity bottleneck.

**Mechanism**:
- At step 150, reduce max speed on lanes `100#0_0` and `101#0_0` to 2 m/s (7.2 km/h)
- Normal speed: 27.78 m/s -> reduced to ~7% of capacity
- Maintained for 750 steps (until step 900)

**Expected congestion pattern**:
```
Step 0-150:    Normal flow
Step 150-300:  Gradual density buildup (vehicles arrive faster than depart)
Step 300-900:  Sustained high density on bottleneck + upstream lanes
Step 900+:     Speed restored, rapid recovery
```

**TraCI APIs used**:
- `traci.lane.setMaxSpeed(lane, speed)` - reduce speed limit
- `traci.lane.getMaxSpeed(lane)` - save original speed for restoration

---

### Scenario 4: Cascading Congestion (Combined Stress)
**File**: `src/scenarios/congestion/scenario_cascading.py`

**Concept**: The most severe scenario - combines all three congestion triggers simultaneously to create network-wide gridlock that cascades across all lanes.

**Mechanism**:
- **Phase 1 (step 100-1200)**: Demand surge - inject 6 vehicles every 8 steps
- **Phase 2 (step 300-900)**: Incident - block 3 vehicles on lane `100#0_0`
- **Phase 3 (step 400-1000)**: Bottleneck - reduce speed on lane `-100#1_0` to 1.5 m/s

**Timeline**:
```
Step 0-100:     Normal baseline
Step 100-300:   Demand surge begins, density rising
Step 300-400:   + Incident on 100#0_0, partial gridlock
Step 400-900:   All 3 active: network-wide congestion, Rc >> 1.0
Step 900-1000:  Incident cleared, still bottleneck + surge
Step 1000-1200: Bottleneck cleared, only surge remains
Step 1200+:     Full recovery phase
```

## 5. Architecture & Code Reuse

All scenarios share a common architecture that reuses existing modules:

```
BaseScenario (src/scenarios/congestion/base_scenario.py)
├── SumoEnv          (src/physical/sumo_env.py)       - SUMO lifecycle
├── StateSync        (src/twin/state_sync.py)         - physical -> twin sync
│   ├── get_lane_data()  (src/physical/detectors.py)  - lane metrics
│   └── compute_density() (src/twin/feature_extractor.py)
├── TrafficState     (src/twin/state_model.py)        - density/speed/queue
├── RiskManager      (src/application/risk/risk_manager.py)
│   ├── congestion_risk()  (src/application/risk/congestion.py)
│   ├── spillback_risk()   (src/application/risk/spillback.py)
│   └── instability_risk() (src/application/risk/instability.py)
└── CSV Logger       (built into BaseScenario)
```

### Class Hierarchy
```python
BaseScenario                    # Shared runner, metrics, CSV export
├── DemandSurgeScenario         # Override: inject_perturbation()
├── IncidentScenario            # Override: inject_perturbation()
├── BottleneckScenario          # Override: inject_perturbation()
└── CascadingCongestionScenario # Override: inject_perturbation()
```

### Per-Step Loop (same as main.py)
```
1. env.step()                    # advance SUMO
2. inject_perturbation(step)     # scenario-specific trigger
3. sync.sync()                   # extract lane data
4. state.update()                # update TrafficState
5. risk_manager.compute(state)   # calculate Rc, Ri, Rs
6. collect_metrics()             # log to CSV
```

## 6. Metrics Collected

Each step records:
| Field             | Description                              |
|-------------------|------------------------------------------|
| step              | Simulation timestep                      |
| vehicle_count     | Total active vehicles in network         |
| avg_congestion    | Mean Rc across all lanes                 |
| max_congestion    | Peak Rc (worst lane)                     |
| avg_spillback     | Mean spillback risk                      |
| max_spillback     | Peak spillback risk                      |
| congested_lanes   | Count of lanes with Rc > 0.6            |
| total_lanes       | Total monitored lanes                    |
| worst_lane        | Lane ID with highest Rc                  |

## 7. How to Run

```bash
# Run all scenarios sequentially
python -m src.scenarios.congestion.run_all

# Run a specific scenario by name (supports partial match)
python -m src.scenarios.congestion.run_all surge
python -m src.scenarios.congestion.run_all incident cascading

# List available scenarios
python -m src.scenarios.congestion.run_all --list

# Run individual scenario directly
python -m src.scenarios.congestion.scenario_demand_surge
python -m src.scenarios.congestion.scenario_incident
python -m src.scenarios.congestion.scenario_bottleneck
python -m src.scenarios.congestion.scenario_cascading
```

Results are exported to `outputs/scenarios/<scenario_name>_<timestamp>.csv`.

## 8. Expected Validation

A scenario successfully demonstrates congestion risk when:
1. `avg_congestion` exceeds 0.6 during the perturbation window
2. `max_congestion` exceeds 1.0 (jam density reached)
3. `congested_lanes` count increases during perturbation
4. Metrics show clear before/during/after pattern
5. Recovery is visible after perturbation ends
