"""
Scenario 1: Junction Blockage
==============================
Blocks vehicles at the central junction (J2) exit, preventing through-traffic.
Queues build up on all 4 approach lanes and propagate upstream to boundary
junctions, causing classic spillback.

Spillback mechanism:
  - Stopped vehicles on exit lanes prevent J2 from clearing
  - Approach lanes (-100#1_0, -101#1_0, 100#0_0, 101#0_0) queue up
  - Queues grow until they spill back to boundary junctions (J1, J3, J4, J5)
  - Rs = queue / lane_length increases on all affected lanes

Network:
        J5 (101#1_0)
        |
  J1 -- J2 -- J3 (100#1_0)
        |
        J4 (-101#0_0)
"""

import traci
from src.scenarios.spillback.base_scenario import SpillbackBaseScenario


class JunctionBlockageScenario(SpillbackBaseScenario):

    def __init__(self, total_steps=None, block_start=200, block_end=800,
                 target_lanes=None, num_blocked=3):
        super().__init__(total_steps=total_steps)
        self.block_start = block_start
        self.block_end = block_end
        # Block the exit lanes from central junction 2
        self.target_lanes = target_lanes or ["100#1_0", "-100#0_0"]
        self.num_blocked = num_blocked
        self.blocked_vehicles = set()

    def get_name(self):
        return "junction_blockage"

    def get_description(self):
        return (
            f"Block {self.num_blocked} vehicles on J2 exits {self.target_lanes} "
            f"from step {self.block_start} to {self.block_end}"
        )

    def inject_perturbation(self, step):
        if step < self.block_start:
            return

        if self.block_start <= step <= self.block_end:
            self._enforce_blockage()

        if step == self.block_end + 1:
            self._clear_blockage()

    def _enforce_blockage(self):
        """Find and block vehicles on exit lanes, keep them stopped."""
        # Keep existing blocks (only those still in simulation)
        active = set(traci.vehicle.getIDList())
        self.blocked_vehicles &= active
        for veh_id in self.blocked_vehicles:
            traci.vehicle.setSpeed(veh_id, 0)

        # Add more if needed
        total_needed = self.num_blocked * len(self.target_lanes)
        if len(self.blocked_vehicles) >= total_needed:
            return

        for lane in self.target_lanes:
            try:
                veh_ids = traci.lane.getLastStepVehicleIDs(lane)
                for veh_id in veh_ids:
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
        print(f"\n  [JUNCTION-BLOCK] Releasing {len(to_release)} vehicles")
        for veh_id in to_release:
            traci.vehicle.setSpeed(veh_id, -1)
        self.blocked_vehicles.clear()


def run():
    scenario = JunctionBlockageScenario()
    scenario.run()


if __name__ == "__main__":
    run()
