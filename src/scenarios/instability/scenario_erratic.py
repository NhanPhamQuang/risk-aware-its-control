"""
Scenario 3: Erratic Speed Fluctuation
======================================
Randomly forces vehicles to change speed dramatically every few steps,
simulating aggressive or distracted driving behavior.

Instability mechanism:
  - Vehicles randomly accelerate or brake with no predictable pattern
  - Neighboring vehicles must react to sudden speed changes
  - Creates maximum speed variance across vehicles on the same lane
  - CV spikes because no two vehicles are moving at similar speeds
"""

import traci
import random
from src.scenarios.instability.base_scenario import InstabilityBaseScenario


class ErraticSpeedScenario(InstabilityBaseScenario):

    def __init__(self, total_steps=None, affected_fraction=0.3,
                 fluctuation_interval=5, start_step=100, end_step=1000):
        super().__init__(total_steps=total_steps)
        self.affected_fraction = affected_fraction  # fraction of vehicles affected
        self.fluctuation_interval = fluctuation_interval  # steps between speed changes
        self.start_step = start_step
        self.end_step = end_step

        self.target_lanes = ["100#0_0", "-100#1_0", "101#0_0", "-101#1_0"]
        self.erratic_vehicles = set()

    def get_name(self):
        return "erratic_speed_fluctuation"

    def get_description(self):
        return (
            f"Randomly fluctuate {int(self.affected_fraction*100)}% of vehicle speeds "
            f"every {self.fluctuation_interval} steps (step {self.start_step}-{self.end_step})"
        )

    def inject_perturbation(self, step):
        """Apply random speed changes to a fraction of vehicles."""
        if step < self.start_step or step > self.end_step:
            # Recovery phase: release all controlled vehicles
            if step == self.end_step + 1:
                self._release_all()
            return

        if step % self.fluctuation_interval != 0:
            return

        self._apply_erratic_speeds()

    def _apply_erratic_speeds(self):
        """Set random speeds on a fraction of vehicles per target lane."""
        for lane in self.target_lanes:
            try:
                veh_ids = traci.lane.getLastStepVehicleIDs(lane)
                if not veh_ids:
                    continue

                # Select a fraction of vehicles to affect
                num_to_affect = max(1, int(len(veh_ids) * self.affected_fraction))
                affected = random.sample(list(veh_ids), min(num_to_affect, len(veh_ids)))

                for veh in affected:
                    # Random speed between 0 and max lane speed
                    # Extreme values create maximum variance
                    rand_val = random.random()
                    if rand_val < 0.3:
                        # 30% chance: near-stop (0-2 m/s)
                        target_speed = random.uniform(0, 2)
                    elif rand_val < 0.6:
                        # 30% chance: crawl (3-8 m/s)
                        target_speed = random.uniform(3, 8)
                    else:
                        # 40% chance: fast (15-27 m/s)
                        target_speed = random.uniform(15, 27)

                    traci.vehicle.setSpeed(veh, target_speed)
                    traci.vehicle.setColor(veh, (255, 0, 255, 255))  # magenta
                    self.erratic_vehicles.add(veh)

            except traci.exceptions.TraCIException:
                continue

    def _release_all(self):
        """Release vehicles that are still in the simulation."""
        active = set(traci.vehicle.getIDList())
        to_release = self.erratic_vehicles & active
        print(f"\n  [ERRATIC] Releasing {len(to_release)} vehicles (of {len(self.erratic_vehicles)} tracked)")
        for veh in to_release:
            traci.vehicle.setSpeed(veh, -1)
        self.erratic_vehicles.clear()


def run():
    scenario = ErraticSpeedScenario()
    scenario.run()


if __name__ == "__main__":
    run()
