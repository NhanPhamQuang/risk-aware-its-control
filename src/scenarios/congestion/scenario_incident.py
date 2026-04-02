"""
Scenario 2: Incident / Lane Blockage
=====================================
Simulates a traffic incident (accident, breakdown) by forcing vehicles
to stop on critical lanes, creating a bottleneck.

Congestion mechanism:
  - Stopped vehicles block the lane
  - Upstream vehicles queue behind the blockage
  - Density spikes on blocked lane and propagates upstream
  - spillback_risk and congestion_risk both increase
"""

import traci
from src.scenarios.congestion.base_scenario import BaseScenario


class IncidentScenario(BaseScenario):

    def __init__(self, total_steps=None, incident_start=200, incident_end=800,
                 target_lanes=None, num_blocked=3):
        super().__init__(total_steps=total_steps)
        self.incident_start = incident_start
        self.incident_end = incident_end
        self.target_lanes = target_lanes or ["100#0_0", "-100#1_0"]
        self.num_blocked = num_blocked   # vehicles to block per lane
        self.blocked_vehicles = set()

    def get_name(self):
        return "incident_blockage"

    def get_description(self):
        return (
            f"Block {self.num_blocked} vehicles on lanes {self.target_lanes} "
            f"from step {self.incident_start} to {self.incident_end}"
        )

    def inject_perturbation(self, step):
        """Block vehicles on target lanes to simulate incident."""
        if step == self.incident_start:
            self._create_blockage()

        # Maintain blockage: keep blocked vehicles stopped
        if self.incident_start <= step <= self.incident_end:
            self._enforce_blockage()

        # Clear incident
        if step == self.incident_end + 1:
            self._clear_blockage()

    def _create_blockage(self):
        """Find and stop vehicles on target lanes."""
        print(f"\n  [INCIDENT] Creating blockage on {self.target_lanes}")

        for lane in self.target_lanes:
            try:
                vehicles_on_lane = traci.lane.getLastStepVehicleIDs(lane)
                to_block = vehicles_on_lane[:self.num_blocked]

                for veh_id in to_block:
                    traci.vehicle.setSpeed(veh_id, 0)     # force stop
                    traci.vehicle.setColor(veh_id, (255, 0, 0, 255))  # red marker
                    self.blocked_vehicles.add(veh_id)

                print(f"    Blocked {len(to_block)} vehicles on {lane}")

            except traci.exceptions.TraCIException:
                continue

        # If not enough vehicles on target lanes, wait and retry next steps
        if len(self.blocked_vehicles) == 0:
            print("    No vehicles found yet - will retry next steps")

    def _enforce_blockage(self):
        """Keep blocked vehicles stopped and try to block more if needed."""
        # Keep existing blocks (only those still in simulation)
        active = set(traci.vehicle.getIDList())
        gone = self.blocked_vehicles - active
        self.blocked_vehicles -= gone
        for veh_id in self.blocked_vehicles:
            traci.vehicle.setSpeed(veh_id, 0)

        # Try to add more blocked vehicles if we don't have enough
        total_needed = self.num_blocked * len(self.target_lanes)
        if len(self.blocked_vehicles) < total_needed:
            for lane in self.target_lanes:
                try:
                    vehicles_on_lane = traci.lane.getLastStepVehicleIDs(lane)
                    for veh_id in vehicles_on_lane:
                        if veh_id not in self.blocked_vehicles:
                            traci.vehicle.setSpeed(veh_id, 0)
                            traci.vehicle.setColor(veh_id, (255, 0, 0, 255))
                            self.blocked_vehicles.add(veh_id)
                            if len(self.blocked_vehicles) >= total_needed:
                                return
                except traci.exceptions.TraCIException:
                    continue

    def _clear_blockage(self):
        """Release blocked vehicles that are still in the simulation."""
        active = set(traci.vehicle.getIDList())
        to_release = self.blocked_vehicles & active
        print(f"\n  [INCIDENT] Clearing blockage - releasing {len(to_release)} vehicles")
        for veh_id in to_release:
            traci.vehicle.setSpeed(veh_id, -1)
            traci.vehicle.setColor(veh_id, (255, 255, 0, 255))
        self.blocked_vehicles.clear()


def run():
    scenario = IncidentScenario()
    scenario.run()


if __name__ == "__main__":
    run()
