# Instability Risk Scenario Plan

## 1. Objective

Design and implement simulation scenarios that trigger **instability risk** in the Risk-Aware ITS Digital Twin system. Instability risk measures speed variance across vehicles on a lane - when vehicles move at very different speeds (some fast, some stopped), the traffic flow is unstable and prone to shockwaves, accidents, and cascading breakdown.

## 2. Background: Instability Risk

### Definition
Traffic flow instability is the tendency of vehicle speeds to oscillate. In stable flow, all vehicles move at roughly the same speed. In unstable flow, speeds vary widely - some vehicles are fast, others are crawling or stopped, creating stop-and-go waves.

### Metric: Coefficient of Variation (CV)
```
Ri = std(vehicle_speeds) / mean(vehicle_speeds)
```
Where `vehicle_speeds` are the individual speeds of all vehicles on a lane at a given timestep.

| Ri Range | Meaning                        |
|----------|--------------------------------|
| 0.0-0.1  | Stable flow (uniform speeds)   |
| 0.1-0.3  | Minor fluctuations             |
| 0.3-0.6  | Unstable (stop-and-go forming) |
| > 0.6    | Highly unstable (shockwaves)   |

### Existing Implementation Issue
The current `instability_risk()` in `src/application/risk/instability.py`:
```python
def instability_risk(speed):
    return np.std([speed]) / (speed + 1e-5) if speed > 0 else 0
```
This takes a **single lane-average speed** value and computes `np.std([single_value])` which is always **0**. The function always returns 0 regardless of actual traffic conditions.

### Fix in Instability Base Scenario
The `InstabilityBaseScenario` computes proper instability using per-vehicle speeds:
```python
veh_ids = traci.lane.getLastStepVehicleIDs(lane)
speeds = [traci.vehicle.getSpeed(v) for v in veh_ids]
Ri = np.std(speeds) / np.mean(speeds)  # proper CV
```
This requires >= 2 vehicles on a lane to be meaningful.

## 3. Causes of Traffic Flow Instability

1. **Stop-and-go waves**: A vehicle brakes, the follower overreacts, creating amplifying shockwaves upstream
2. **Mixed speed traffic**: Slow and fast vehicles on the same lane create speed differential
3. **Aggressive/erratic driving**: Unpredictable speed changes force reactive braking
4. **Oscillating conditions**: Rapidly changing speed limits prevent flow from stabilizing
5. **Near-capacity flow**: At moderate-high density, small perturbations amplify into waves

## 4. Scenario Designs

### Scenario 1: Stop-and-Go Wave
**File**: `src/scenarios/instability/scenario_stop_and_go.py`

**Concept**: Periodically forces vehicles to brake to 0 on key lanes, creating shockwaves that propagate upstream. Vehicles behind alternate between stopping and accelerating.

**Mechanism**:
- Every 30 steps, stop one vehicle (middle of lane) for 10 steps
- Target lanes: `100#0_0`, `-100#1_0`, `101#0_0`
- Active from step 100 to 1000

**Expected instability pattern**:
```
Step 0-100:     Stable flow (Ri ~0)
Step 100-200:   First waves forming (Ri 0.1-0.3)
Step 200-1000:  Persistent stop-and-go (Ri 0.3-0.8)
Step 1000+:     Recovery, waves dissipate (Ri decreasing)
```

**TraCI APIs**:
- `traci.vehicle.setSpeed(veh, 0)` - force brake
- `traci.vehicle.setSpeed(veh, -1)` - release to automatic
- `traci.lane.getLastStepVehicleIDs()` - find vehicles to brake

---

### Scenario 2: Mixed Speed Fleet
**File**: `src/scenarios/instability/scenario_mixed_speed.py`

**Concept**: Injects slow vehicles (~3 m/s) among normal fast traffic (~28 m/s). The speed differential creates moving bottlenecks and accordion effects.

**Mechanism**:
- Every 15 steps, inject one slow vehicle (max speed 3 m/s) with a random route
- Normal traffic speed: 27.78 m/s (100 km/h)
- Active from step 100 to 900

**Expected instability pattern**:
```
Step 0-100:     Normal flow, all vehicles ~28 m/s (Ri ~0)
Step 100-300:   Slow vehicles appear, fast vehicles brake behind them (Ri 0.2-0.5)
Step 300-900:   Steady state with mixed speeds (Ri 0.3-0.7)
Step 900+:      Slow vehicles clear, flow stabilizes
```

**TraCI APIs**:
- `traci.vehicle.add()` + `traci.route.add()` - inject vehicles
- `traci.vehicle.setMaxSpeed(veh, 3.0)` - cap vehicle speed

---

### Scenario 3: Erratic Speed Fluctuation
**File**: `src/scenarios/instability/scenario_erratic.py`

**Concept**: Randomly sets vehicle speeds to extreme values (0-2 m/s, 3-8 m/s, or 15-27 m/s) every 5 steps, simulating aggressive or distracted driving.

**Mechanism**:
- Every 5 steps, select 30% of vehicles on target lanes
- Assign random speed: 30% near-stop, 30% crawl, 40% fast
- Active from step 100 to 1000

**Expected instability pattern**:
```
Step 0-100:     Normal flow (Ri ~0)
Step 100-1000:  Maximum instability - vehicles at wildly different speeds (Ri 0.5-1.0+)
Step 1000+:     All vehicles released to auto, rapid recovery
```

**TraCI APIs**:
- `traci.vehicle.setSpeed(veh, target)` - force specific speed
- `traci.lane.getLastStepVehicleIDs()` - select vehicles to affect

---

### Scenario 4: Oscillating Speed Limit
**File**: `src/scenarios/instability/scenario_oscillating_limit.py`

**Concept**: Cycles lane speed limits between high (27.78 m/s) and low (3 m/s) every 20 steps. Vehicles at the front respond first, creating speed waves along the lane.

**Mechanism**:
- Cycle period: 40 steps (20 high, 20 low)
- Target lanes: `100#0_0`, `-100#1_0`
- Active from step 150 to 1000

**Expected instability pattern**:
```
Step 0-150:     Normal flow
Step 150-1000:  Persistent oscillation, vehicles never reach steady state
                Front vehicles accelerate/brake first, rear follows with delay
                At any moment: CV > 0.3 due to speed gradient along lane
Step 1000+:     Speed restored, flow stabilizes
```

**TraCI APIs**:
- `traci.lane.setMaxSpeed(lane, speed)` - change speed limit
- `traci.lane.getMaxSpeed(lane)` - save original for restoration

## 5. Architecture & Code Reuse

```
InstabilityBaseScenario (src/scenarios/instability/base_scenario.py)
├── SumoEnv              (src/physical/sumo_env.py)         - SUMO lifecycle
├── StateSync            (src/twin/state_sync.py)           - physical -> twin sync
│   ├── get_lane_data()  (src/physical/detectors.py)        - lane metrics
│   └── compute_density()(src/twin/feature_extractor.py)
├── TrafficState         (src/twin/state_model.py)          - density/speed/queue
├── RiskManager          (src/application/risk/risk_manager.py)
│   ├── congestion_risk()
│   ├── spillback_risk()
│   └── instability_risk()  [NOTE: always returns 0 - see fix below]
├── _compute_instability() [NEW: proper per-vehicle CV computation]
└── CSV Logger             (built into InstabilityBaseScenario)
```

### Key Difference from Congestion Base
The `InstabilityBaseScenario._compute_instability()` method collects per-vehicle speeds:
```python
veh_ids = traci.lane.getLastStepVehicleIDs(lane)
speeds = [traci.vehicle.getSpeed(v) for v in veh_ids]
CV = np.std(speeds) / np.mean(speeds)
```
This bypasses the broken `instability_risk()` function and provides the real instability metric.

### Class Hierarchy
```python
InstabilityBaseScenario          # Shared runner, proper CV metrics, CSV export
├── StopAndGoScenario            # Override: inject_perturbation()
├── MixedSpeedScenario           # Override: inject_perturbation()
├── ErraticSpeedScenario         # Override: inject_perturbation()
└── OscillatingLimitScenario     # Override: inject_perturbation()
```

## 6. Metrics Collected

Each step records:
| Field             | Description                               |
|-------------------|-------------------------------------------|
| step              | Simulation timestep                       |
| vehicle_count     | Total active vehicles in network          |
| avg_instability   | Mean CV across all lanes                  |
| max_instability   | Peak CV (worst lane)                      |
| avg_congestion    | Mean congestion risk (from RiskManager)   |
| max_congestion    | Peak congestion risk                      |
| unstable_lanes    | Count of lanes with CV > 0.3             |
| total_lanes       | Total monitored lanes                     |
| worst_lane        | Lane ID with highest CV                   |
| worst_lane_cv     | CV value of the worst lane                |

## 7. How to Run

```bash
# Run all instability scenarios
python -m src.scenarios.instability.run_all

# Run by name (supports partial match)
python -m src.scenarios.instability.run_all stopgo
python -m src.scenarios.instability.run_all mixed erratic

# List available scenarios
python -m src.scenarios.instability.run_all --list

# Run individual scenario
python -m src.scenarios.instability.scenario_stop_and_go
python -m src.scenarios.instability.scenario_mixed_speed
python -m src.scenarios.instability.scenario_erratic
python -m src.scenarios.instability.scenario_oscillating_limit
```

Results exported to `outputs/scenarios/<scenario_name>_<timestamp>.csv`.

## 8. Expected Validation

A scenario successfully demonstrates instability risk when:
1. `avg_instability` (CV) exceeds 0.3 during the perturbation window
2. `max_instability` exceeds 0.6 (strong shockwaves)
3. `unstable_lanes` count increases during perturbation
4. Clear before/during/after pattern in the metrics
5. Recovery visible after perturbation ends
6. Instability and congestion behave differently (instability can be high even at moderate density)
