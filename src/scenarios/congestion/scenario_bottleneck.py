"""
Scenario 3: Bottleneck via Speed Reduction
==========================================
Simulates road works or construction zones by drastically reducing
the max speed on key lanes, creating a capacity bottleneck.

Congestion mechanism:
  - Reduced speed limit -> vehicles slow down
  - Upstream vehicles arrive faster than they can pass through
  - Density builds up on the bottleneck lane and upstream
  - congestion_risk = density / jam_density increases
"""

import traci
from src.scenarios.congestion.base_scenario import BaseScenario


class BottleneckScenario(BaseScenario):

    def __init__(self, total_steps=None, bottleneck_start=150, bottleneck_end=900,
                 target_lanes=None, reduced_speed=2.0):
        super().__init__(total_steps=total_steps)
        self.bottleneck_start = bottleneck_start
        self.bottleneck_end = bottleneck_end
        # Target the central lanes where multiple routes converge
        self.target_lanes = target_lanes or ["100#0_0", "101#0_0"]
        self.reduced_speed = reduced_speed      # m/s (~7.2 km/h, crawl speed)
        self.original_speeds = {}

    def get_name(self):
        return "bottleneck_speed_reduction"

    def get_description(self):
        return (
            f"Reduce speed to {self.reduced_speed} m/s on {self.target_lanes} "
            f"from step {self.bottleneck_start} to {self.bottleneck_end}"
        )

    def inject_perturbation(self, step):
        """Apply/remove speed reduction."""
        if step == self.bottleneck_start:
            self._apply_bottleneck()

        if step == self.bottleneck_end + 1:
            self._remove_bottleneck()

    def _apply_bottleneck(self):
        """Reduce max speed on target lanes."""
        print(f"\n  [BOTTLENECK] Reducing speed on {self.target_lanes} to {self.reduced_speed} m/s")

        for lane in self.target_lanes:
            try:
                # Save original speed for restoration
                original = traci.lane.getMaxSpeed(lane)
                self.original_speeds[lane] = original

                traci.lane.setMaxSpeed(lane, self.reduced_speed)

                print(f"    {lane}: {original:.1f} -> {self.reduced_speed} m/s")
            except traci.exceptions.TraCIException as e:
                print(f"    Failed on {lane}: {e}")

    def _remove_bottleneck(self):
        """Restore original speeds."""
        print(f"\n  [BOTTLENECK] Restoring original speeds")

        for lane, original_speed in self.original_speeds.items():
            try:
                traci.lane.setMaxSpeed(lane, original_speed)
                print(f"    {lane}: restored to {original_speed:.1f} m/s")
            except traci.exceptions.TraCIException:
                continue

        self.original_speeds.clear()


def run():
    scenario = BottleneckScenario()
    scenario.run()


if __name__ == "__main__":
    run()
