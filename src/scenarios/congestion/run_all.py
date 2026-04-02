"""
Run all congestion risk scenarios sequentially.
Each scenario launches its own SUMO instance and exports results to CSV.

Usage:
    python -m src.scenarios.congestion.run_all                  # run all scenarios
    python -m src.scenarios.congestion.run_all surge             # run by name
    python -m src.scenarios.congestion.run_all incident cascading # run multiple by name
    python -m src.scenarios.congestion.run_all --list            # show available scenarios
"""

import sys
from src.scenarios.congestion.scenario_demand_surge import DemandSurgeScenario
from src.scenarios.congestion.scenario_incident import IncidentScenario
from src.scenarios.congestion.scenario_bottleneck import BottleneckScenario
from src.scenarios.congestion.scenario_cascading import CascadingCongestionScenario


SCENARIOS = {
    "surge":      ("Demand Surge", DemandSurgeScenario),
    "incident":   ("Incident Blockage", IncidentScenario),
    "bottleneck": ("Bottleneck Speed Reduction", BottleneckScenario),
    "cascading":  ("Cascading Congestion", CascadingCongestionScenario),
}


def _find_scenario(arg):
    """Match argument to scenario name (supports partial match)."""
    arg_lower = arg.lower()
    for key in SCENARIOS:
        if key.startswith(arg_lower):
            return key
    return None


def main():
    args = sys.argv[1:]

    # Show available scenarios
    if "--list" in args or "-l" in args:
        print("\nAvailable scenarios:")
        for key, (name, _) in SCENARIOS.items():
            print(f"  {key:<12} - {name}")
        print()
        return

    # Parse which scenarios to run
    if args:
        selected = []
        for arg in args:
            match = _find_scenario(arg)
            if match:
                selected.append(match)
            else:
                print(f"Unknown scenario '{arg}'. Use --list to see available scenarios.")
        if not selected:
            return
    else:
        selected = list(SCENARIOS.keys())

    print(f"\n{'#'*60}")
    print(f"  CONGESTION RISK SCENARIO RUNNER")
    print(f"  Running: {', '.join(selected)}")
    print(f"{'#'*60}\n")

    for key in selected:
        name, cls = SCENARIOS[key]
        print(f"\n>>> Starting: {name} ({key})")

        try:
            scenario = cls()
            scenario.run()
        except Exception as e:
            print(f"Scenario '{key}' failed: {e}")
            import traceback
            traceback.print_exc()

        print(f"<<< {name} complete\n")

    print(f"\n{'#'*60}")
    print(f"  ALL SCENARIOS COMPLETE")
    print(f"  Results saved in: outputs/scenarios/")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()
