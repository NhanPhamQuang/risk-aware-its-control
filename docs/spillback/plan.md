# Spillback Risk Scenario Plan

## 1. Objective

Design and implement simulation scenarios that trigger **spillback risk** in the Risk-Aware ITS Digital Twin system. Spillback occurs when vehicle queues overflow beyond a lane's storage capacity, blocking upstream intersections and propagating through the network - a fundamentally different problem from localized congestion.

## 2. Background: Spillback Risk

### Definition
Spillback is the propagation of blocked queues through a road network. When a queue on one lane exceeds its capacity, it physically blocks the upstream junction, preventing vehicles on OTHER approach lanes from proceeding. This creates a chain reaction that can gridlock an entire network.

### How Spillback Differs from Congestion
| Aspect     | Congestion                    | Spillback                           |
|------------|-------------------------------|--------------------------------------|
| Scope      | Localized to one lane/link    | Propagates across multiple junctions |
| Cause      | Demand > capacity             | Queue overflow blocks upstream       |
| Metric     | Density / jam_density         | Queue / lane_capacity                |
| Recovery   | Demand drops -> clears        | Requires ALL queues to clear         |
| Danger     | Slow traffic                  | Complete gridlock (deadlock)         |

### Formula (from `src/application/risk/spillback.py`)
```
Rs = queue / lane_length
```
Where:
- `queue` = `traci.lane.getLastStepHaltingNumber(lane)` (halted vehicles)
- `lane_length` = 50 (default capacity parameter)

### Risk Levels
| Rs Range | Meaning                        |
|----------|--------------------------------|
| 0.0-0.1  | Normal (< 5 queued vehicles)   |
| 0.1-0.3  | Building queue                 |
| 0.3-0.5  | Significant queue              |
| 0.5-1.0  | Approaching overflow           |
| > 1.0    | Spillback active (overflow)    |

### Enhanced Metrics in SpillbackBaseScenario
Beyond the basic Rs, the base scenario also tracks:
- **Queue propagation**: Detects when both a lane AND its downstream lane have queues simultaneously (true spillback, not just local queuing)
- **Total network queue**: Sum of all halted vehicles across all lanes
- **Propagating lanes**: Count of lanes where spillback is actively spreading

## 3. Network Topology for Spillback Analysis

```
        J5 (boundary north)
        |
        101#1_0 (exit N)
        |
  J1 -- J2 (central hub) -- J3
        |
        -101#0_0 (exit S)
        |
        J4 (boundary south)
```

**Junction 2 (central hub)** - 4 approach + 4 exit lanes:
| Direction | Approach Lane | Exit Lane  |
|-----------|---------------|------------|
| East      | 100#0_0       | 100#1_0    |
| West      | -100#1_0      | -100#0_0   |
| North     | 101#0_0       | 101#1_0    |
| South     | -101#1_0      | -101#0_0   |

**Spillback path**: Block exit lanes -> approach lanes queue -> overflow blocks boundary junctions -> their approach lanes queue.

## 4. Scenario Designs

### Scenario 1: Junction Blockage
**File**: `src/scenarios/spillback/scenario_junction_blockage.py`

**Concept**: Blocks vehicles on J2 exit lanes (100#1_0, -100#0_0), preventing through-traffic. Queues build on all approach lanes and propagate upstream.

**Mechanism**:
- At step 200, stop 3 vehicles each on east and west exit lanes
- Maintain blockage until step 800
- Approach lanes queue because J2 can't clear

**Expected spillback pattern**:
```
Step 0-200:     Normal flow (Rs ~0)
Step 200-300:   Queue forming on approach lanes (Rs 0.1-0.3)
Step 300-800:   Queue overflows, blocks upstream junctions (Rs > 0.5)
Step 800+:      Blockage cleared, slow recovery due to queued vehicles
```

**TraCI APIs**: `traci.vehicle.setSpeed(veh, 0)`, `traci.lane.getLastStepVehicleIDs()`

---

### Scenario 2: Downstream Capacity Reduction
**File**: `src/scenarios/spillback/scenario_downstream_reduction.py`

**Concept**: Reduces speed on ALL 4 exit lanes from J2 to 1.5 m/s (~5.4 km/h), strangling junction throughput. Vehicles can't exit fast enough, causing approach lane overflow.

**Mechanism**:
- At step 150, reduce all 4 J2 exit lanes to 1.5 m/s
- Normal throughput ~28 m/s -> reduced to 5% capacity
- Maintained until step 900

**Expected spillback pattern**:
```
Step 0-150:     Normal flow
Step 150-300:   Gradual queue buildup on all 4 approach lanes
Step 300-900:   Sustained spillback, queues propagate to boundary junctions
Step 900+:      Speed restored, gradual queue drain
```

**TraCI APIs**: `traci.lane.setMaxSpeed()`, `traci.lane.getMaxSpeed()`

---

### Scenario 3: Queue Saturation via Demand Flood
**File**: `src/scenarios/spillback/scenario_demand_flood.py`

**Concept**: Floods J2 with targeted demand - all injected vehicles must pass through J2, overwhelming its clearance capacity.

**Mechanism**:
- Every 8 steps, inject 10 vehicles with routes through J2
- Routes cover all 4 approach directions
- Active from step 100 to 900
- Total injected: ~1000 extra vehicles, all funneled through J2

**Expected spillback pattern**:
```
Step 0-100:     Normal baseline demand
Step 100-300:   Queue building at J2 approach lanes
Step 300-900:   J2 saturated, queues overflow to boundary junctions
Step 900+:      Injection stops, slow recovery as excess clears
```

**TraCI APIs**: `traci.route.add()`, `traci.vehicle.add()`

---

### Scenario 4: Cascading Spillback (Chain Reaction)
**File**: `src/scenarios/spillback/scenario_cascading_spillback.py`

**Concept**: Most severe scenario - combines demand flood with progressive exit blockage to create network-wide deadlock.

**Timeline**:
```
Step 100-1200:  Demand flood (8 vehicles every 10 steps)
Step 250-900:   Block E/W exit lanes (100#1_0, -100#0_0)
Step 400-800:   Block N/S exit lanes (101#1_0, -101#0_0)
```

**Expected spillback pattern**:
```
Step 0-100:     Normal flow
Step 100-250:   Demand rising, light queuing at J2
Step 250-400:   E/W exits blocked, N/S still open -> partial spillback
Step 400-800:   ALL exits blocked + high demand -> complete gridlock
                Rs >> 1.0 on all approach lanes
                Propagation to all boundary junctions
Step 800-900:   N/S exits cleared, partial relief
Step 900-1200:  E/W exits cleared, still high demand
Step 1200+:     Full recovery phase
```

## 5. Architecture & Code Reuse

```
SpillbackBaseScenario (src/scenarios/spillback/base_scenario.py)
├── SumoEnv              (src/physical/sumo_env.py)         - SUMO lifecycle
├── StateSync            (src/twin/state_sync.py)           - physical -> twin sync
│   ├── get_lane_data()  (src/physical/detectors.py)        - lane metrics + halt count
│   └── compute_density()(src/twin/feature_extractor.py)
├── TrafficState         (src/twin/state_model.py)          - density/speed/queue
├── RiskManager          (src/application/risk/risk_manager.py)
│   └── spillback_risk() (src/application/risk/spillback.py) - queue / lane_length
├── _compute_spillback() [NEW: enhanced queue propagation detection]
└── CSV Logger           (built into SpillbackBaseScenario)
```

### Class Hierarchy
```python
SpillbackBaseScenario              # Shared runner, spillback metrics, propagation tracking
├── JunctionBlockageScenario       # Override: inject_perturbation()
├── DownstreamReductionScenario    # Override: inject_perturbation()
├── DemandFloodScenario            # Override: inject_perturbation()
└── CascadingSpillbackScenario     # Override: inject_perturbation()
```

## 6. Metrics Collected

Each step records:
| Field               | Description                                    |
|---------------------|------------------------------------------------|
| step                | Simulation timestep                            |
| vehicle_count       | Total active vehicles in network               |
| avg_spillback       | Mean Rs across all lanes                       |
| max_spillback       | Peak Rs (worst lane)                           |
| avg_congestion      | Mean congestion risk (from RiskManager)         |
| total_queue         | Sum of halted vehicles across all lanes         |
| max_queue           | Highest queue on any single lane               |
| spillback_lanes     | Lanes with Rs > 0.1 (>5 halted vehicles)       |
| propagating_lanes   | Lanes where queue extends to downstream lane    |
| total_lanes         | Total monitored lanes                          |
| worst_lane          | Lane ID with longest queue                     |
| worst_lane_queue    | Queue count on worst lane                      |

## 7. How to Run

```bash
# Run all spillback scenarios
python -m src.scenarios.spillback.run_all

# Run by name (supports partial match)
python -m src.scenarios.spillback.run_all junction
python -m src.scenarios.spillback.run_all downstream flood

# List available scenarios
python -m src.scenarios.spillback.run_all --list

# Run individual scenario
python -m src.scenarios.spillback.scenario_junction_blockage
python -m src.scenarios.spillback.scenario_downstream_reduction
python -m src.scenarios.spillback.scenario_demand_flood
python -m src.scenarios.spillback.scenario_cascading_spillback
```

Results exported to `outputs/scenarios/<scenario_name>_<timestamp>.csv`.

## 8. Expected Validation

A scenario successfully demonstrates spillback risk when:
1. `max_spillback` (Rs) exceeds 0.5 during perturbation
2. `propagating_lanes` > 0 (queue extends to downstream lanes)
3. `total_queue` grows during perturbation and drops during recovery
4. Clear before/during/after pattern in metrics
5. Spillback on approach lanes correlates with blockage on exit lanes (causality)
6. Recovery is slower than onset (characteristic of spillback vs. simple congestion)
