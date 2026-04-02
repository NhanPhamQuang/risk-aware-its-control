"""
Scenario 4: Oscillating Speed Limit
====================================
Cycles lane speed limits between high and low values on a periodic interval,
forcing all vehicles on the lane to repeatedly accelerate and decelerate.

Instability mechanism:
  - Speed limit drops: vehicles at the front brake first, rear vehicles still fast
  - Speed limit rises: front vehicles accelerate first, rear vehicles still slow
  - At any moment, vehicles on the lane have very different speeds
  - The oscillation prevents the lane from ever reaching stable flow
  - CV remains persistently high throughout the oscillation window
"""

import traci
from src.scenarios.instability.base_scenario import InstabilityBaseScenario


class OscillatingLimitScenario(InstabilityBaseScenario):

    def __init__(self, total_steps=None, target_lanes=None,
                 high_speed=27.78, low_speed=3.0,
                 cycle_period=40, start_step=150, end_step=1000):
        super().__init__(total_steps=total_steps)
        self.target_lanes = target_lanes or ["100#0_0", "-100#1_0"]
        self.high_speed = high_speed    # m/s (normal, ~100 km/h)
        self.low_speed = low_speed      # m/s (crawl, ~11 km/h)
        self.cycle_period = cycle_period  # steps per full cycle (half high, half low)
        self.start_step = start_step
        self.end_step = end_step
        self.original_speeds = {}
        self.current_phase = "high"

    def get_name(self):
        return "oscillating_speed_limit"

    def get_description(self):
        return (
            f"Cycle speed limit {self.low_speed}-{self.high_speed} m/s "
            f"every {self.cycle_period//2} steps on {self.target_lanes} "
            f"(step {self.start_step}-{self.end_step})"
        )

    def inject_perturbation(self, step):
        """Toggle speed limits between high and low."""
        if step == self.start_step:
            self._save_original_speeds()

        if step < self.start_step or step > self.end_step:
            return

        # Restore at end
        if step == self.end_step:
            self._restore_speeds()
            return

        # Determine phase within cycle
        cycle_pos = (step - self.start_step) % self.cycle_period
        half = self.cycle_period // 2

        if cycle_pos == 0:
            # Switch to low speed
            self._set_speeds(self.low_speed)
            self.current_phase = "low"
        elif cycle_pos == half:
            # Switch to high speed
            self._set_speeds(self.high_speed)
            self.current_phase = "high"

    def _save_original_speeds(self):
        """Save original lane speeds for restoration."""
        for lane in self.target_lanes:
            try:
                self.original_speeds[lane] = traci.lane.getMaxSpeed(lane)
            except traci.exceptions.TraCIException:
                pass

    def _set_speeds(self, speed):
        """Set speed limit on all target lanes."""
        for lane in self.target_lanes:
            try:
                traci.lane.setMaxSpeed(lane, speed)
            except traci.exceptions.TraCIException:
                continue

    def _restore_speeds(self):
        """Restore original speed limits."""
        print(f"\n  [OSCILLATING] Restoring original speeds")
        for lane, original in self.original_speeds.items():
            try:
                traci.lane.setMaxSpeed(lane, original)
            except traci.exceptions.TraCIException:
                continue


def run():
    scenario = OscillatingLimitScenario()
    scenario.run()


if __name__ == "__main__":
    run()
