"""
Scenario 1: Stop-and-Go Wave
=============================
Periodically forces vehicles on key lanes to brake to 0, then releases them.
This creates shockwaves that propagate upstream - vehicles behind alternate
between stopping and accelerating, producing high speed variance (CV).

Instability mechanism:
  - Lead vehicle brakes suddenly -> follower brakes harder (overreaction)
  - Wave propagates upstream, amplifying speed oscillations
  - Vehicles on the same lane have wildly different speeds at any moment
  - CV = std(speeds) / mean(speeds) spikes during wave propagation
"""

import traci
from src.scenarios.instability.base_scenario import InstabilityBaseScenario


class StopAndGoScenario(InstabilityBaseScenario):

    def __init__(self, total_steps=None, target_lanes=None,
                 brake_interval=30, brake_duration=10, start_step=100, end_step=1000):
        super().__init__(total_steps=total_steps)
        self.target_lanes = target_lanes or ["100#0_0", "-100#1_0", "101#0_0"]
        self.brake_interval = brake_interval    # steps between brake events
        self.brake_duration = brake_duration    # how long vehicle stays stopped
        self.start_step = start_step
        self.end_step = end_step
        self.braked_vehicles = {}  # veh_id -> release_step

    def get_name(self):
        return "stop_and_go_wave"

    def get_description(self):
        return (
            f"Brake vehicles every {self.brake_interval} steps for {self.brake_duration} steps "
            f"on {self.target_lanes} (step {self.start_step}-{self.end_step})"
        )

    def inject_perturbation(self, step):
        """Periodically brake a vehicle on target lanes, then release."""
        if step < self.start_step or step > self.end_step:
            return

        # Brake phase: find and stop a vehicle on each target lane
        if step % self.brake_interval == 0:
            self._brake_vehicles(step)

        # Release vehicles whose brake duration has expired
        self._release_vehicles(step)

        # Keep braked vehicles stopped
        self._enforce_brakes()

    def _brake_vehicles(self, step):
        """Stop one vehicle per target lane to create a shockwave."""
        for lane in self.target_lanes:
            try:
                veh_ids = traci.lane.getLastStepVehicleIDs(lane)
                if not veh_ids:
                    continue

                # Pick the vehicle closest to the middle of the lane
                # (maximizes upstream impact)
                mid_idx = len(veh_ids) // 2
                veh = veh_ids[mid_idx]

                if veh not in self.braked_vehicles:
                    traci.vehicle.setSpeed(veh, 0)
                    traci.vehicle.setColor(veh, (255, 100, 0, 255))  # orange
                    self.braked_vehicles[veh] = step + self.brake_duration

            except traci.exceptions.TraCIException:
                continue

    def _release_vehicles(self, step):
        """Release vehicles whose brake duration has expired."""
        active = set(traci.vehicle.getIDList())
        to_release = [v for v, release in self.braked_vehicles.items() if step >= release]

        for veh in to_release:
            if veh in active:
                traci.vehicle.setSpeed(veh, -1)
                traci.vehicle.setColor(veh, (0, 255, 0, 255))
            del self.braked_vehicles[veh]

    def _enforce_brakes(self):
        """Keep braked vehicles stopped."""
        active = set(traci.vehicle.getIDList())
        gone = [v for v in self.braked_vehicles if v not in active]
        for v in gone:
            del self.braked_vehicles[v]
        for veh in self.braked_vehicles:
            traci.vehicle.setSpeed(veh, 0)


def run():
    scenario = StopAndGoScenario()
    scenario.run()


if __name__ == "__main__":
    run()
