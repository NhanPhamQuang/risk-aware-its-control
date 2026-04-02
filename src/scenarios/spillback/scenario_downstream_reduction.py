"""
Scenario 2: Downstream Capacity Reduction
==========================================
Reduces speed/capacity on lanes exiting the central junction (J2), so
vehicles can't leave fast enough. Approach lanes queue up and overflow.

Spillback mechanism:
  - Exit lanes slowed to crawl speed (1.5 m/s)
  - Vehicles clear J2 very slowly
  - Approach lanes queue at junction waiting for gaps
  - Queue grows faster than it drains -> spillback to upstream
  - Different from bottleneck: targets junction throughput, not lane speed
"""

import traci
from src.scenarios.spillback.base_scenario import SpillbackBaseScenario


class DownstreamReductionScenario(SpillbackBaseScenario):

    def __init__(self, total_steps=None, start_step=150, end_step=900,
                 target_lanes=None, reduced_speed=1.5):
        super().__init__(total_steps=total_steps)
        self.start_step = start_step
        self.end_step = end_step
        # All exit lanes from central junction 2
        self.target_lanes = target_lanes or [
            "100#1_0", "-100#0_0", "101#1_0", "-101#0_0"
        ]
        self.reduced_speed = reduced_speed  # m/s (~5.4 km/h)
        self.original_speeds = {}

    def get_name(self):
        return "downstream_capacity_reduction"

    def get_description(self):
        return (
            f"Reduce all J2 exit lanes to {self.reduced_speed} m/s "
            f"from step {self.start_step} to {self.end_step}"
        )

    def inject_perturbation(self, step):
        if step == self.start_step:
            self._apply_reduction()

        if step == self.end_step + 1:
            self._restore_speeds()

    def _apply_reduction(self):
        """Reduce speed on all exit lanes from J2."""
        print(f"\n  [DOWNSTREAM] Reducing exit lanes to {self.reduced_speed} m/s")
        for lane in self.target_lanes:
            try:
                original = traci.lane.getMaxSpeed(lane)
                self.original_speeds[lane] = original
                traci.lane.setMaxSpeed(lane, self.reduced_speed)
                print(f"    {lane}: {original:.1f} -> {self.reduced_speed} m/s")
            except traci.exceptions.TraCIException as e:
                print(f"    Failed on {lane}: {e}")

    def _restore_speeds(self):
        """Restore original speeds."""
        print(f"\n  [DOWNSTREAM] Restoring exit lane speeds")
        for lane, original in self.original_speeds.items():
            try:
                traci.lane.setMaxSpeed(lane, original)
            except traci.exceptions.TraCIException:
                continue
        self.original_speeds.clear()


def run():
    scenario = DownstreamReductionScenario()
    scenario.run()


if __name__ == "__main__":
    run()
