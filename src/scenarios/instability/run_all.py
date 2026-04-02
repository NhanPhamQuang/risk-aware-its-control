"""
Run all instability risk scenarios sequentially.
Each scenario launches its own SUMO instance and exports results to CSV.

Usage:
    python -m src.scenarios.instability.run_all                     # run all
    python -m src.scenarios.instability.run_all stopgo               # by name
    python -m src.scenarios.instability.run_all mixed oscillating    # multiple
    python -m src.scenarios.instability.run_all --list               # show available
"""

import sys
from src.scenarios.instability.scenario_stop_and_go import StopAndGoScenario
from src.scenarios.instability.scenario_mixed_speed import MixedSpeedScenario
from src.scenarios.instability.scenario_erratic import ErraticSpeedScenario
from src.scenarios.instability.scenario_oscillating_limit import OscillatingLimitScenario


SCENARIOS = {
    "stopgo":      ("Stop-and-Go Wave", StopAndGoScenario),
    "mixed":       ("Mixed Speed Fleet", MixedSpeedScenario),
    "erratic":     ("Erratic Speed Fluctuation", ErraticSpeedScenario),
    "oscillating": ("Oscillating Speed Limit", OscillatingLimitScenario),
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

    if "--list" in args or "-l" in args:
        print("\nAvailable instability scenarios:")
        for key, (name, _) in SCENARIOS.items():
            print(f"  {key:<12} - {name}")
        print()
        return

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
    print(f"  INSTABILITY RISK SCENARIO RUNNER")
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
