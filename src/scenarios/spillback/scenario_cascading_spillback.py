"""
Scenario 4: Cascading Spillback (Chain Reaction)
=================================================
Blocks multiple exit points simultaneously while flooding demand,
creating chain-reaction spillback that propagates across all junctions.

Spillback mechanism:
  - Phase 1 (demand): heavy vehicle injection through J2
  - Phase 2 (block exits): block 2 exit lanes from J2
  - Phase 3 (block more): block remaining exit lanes
  - Approach lanes overflow, blocking boundary junctions
  - Boundary junctions can't clear, blocking their approach lanes
  - Network-wide gridlock: Rs >> 1.0 on multiple lanes simultaneously
"""

import traci
import random
from src.scenarios.spillback.base_scenario import SpillbackBaseScenario


class CascadingSpillbackScenario(SpillbackBaseScenario):

    def __init__(self, total_steps=None):
        super().__init__(total_steps=total_steps)

        # Phase 1: Demand flood
        self.flood_start = 100
        self.flood_end = 1200
        self.burst_size = 8
        self.burst_interval = 10
        self.veh_counter = 50000

        # Phase 2: Block east+west exits from J2
        self.block1_start = 250
        self.block1_end = 900
        self.block1_lanes = ["100#1_0", "-100#0_0"]

        # Phase 3: Block north+south exits from J2
        self.block2_start = 400
        self.block2_end = 800
        self.block2_lanes = ["101#1_0", "-101#0_0"]

        self.blocked_vehicles = set()
        self.num_blocked_per_lane = 3

        self.edges = ["-100#0", "-100#1", "-101#0", "-101#1",
                      "100#0", "100#1", "101#0", "101#1"]

    def get_name(self):
        return "cascading_spillback"

    def get_description(self):
        return (
            "Demand flood (step 100-1200) + "
            "block E/W exits (step 250-900) + "
            "block N/S exits (step 400-800)"
        )

    def inject_perturbation(self, step):
        self._demand_flood(step)
        self._block_phase1(step)
        self._block_phase2(step)

    # ---- Demand Flood ----
    def _demand_flood(self, step):
        if step < self.flood_start or step > self.flood_end:
            return
        if step % self.burst_interval != 0:
            return

        for _ in range(self.burst_size):
            origin = random.choice(self.edges)
            try:
                links = traci.lane.getLinks(origin + "_0")
                if not links:
                    continue
                dest_lane = random.choice(links)[0]
                dest_edge = traci.lane.getEdgeID(dest_lane)

                veh_id = f"cspill_{self.veh_counter}"
                route_id = f"route_cspill_{self.veh_counter}"
                self.veh_counter += 1

                traci.route.add(route_id, [origin, dest_edge])
                traci.vehicle.add(veh_id, route_id)
            except traci.exceptions.TraCIException:
                continue

    # ---- Block Phase 1: E/W exits ----
    def _block_phase1(self, step):
        if self.block1_start <= step <= self.block1_end:
            self._enforce_block(self.block1_lanes)

        if step == self.block1_end + 1:
            self._release_lanes(self.block1_lanes)
            print(f"  [CASCADE] Released E/W exits")

    # ---- Block Phase 2: N/S exits ----
    def _block_phase2(self, step):
        if self.block2_start <= step <= self.block2_end:
            self._enforce_block(self.block2_lanes)

        if step == self.block2_end + 1:
            self._release_lanes(self.block2_lanes)
            print(f"  [CASCADE] Released N/S exits")

    def _enforce_block(self, lanes):
        """Find and block vehicles on target lanes."""
        for lane in lanes:
            try:
                veh_ids = traci.lane.getLastStepVehicleIDs(lane)
                blocked_on_lane = sum(1 for v in self.blocked_vehicles
                                      if v in set(veh_ids))

                for veh_id in veh_ids:
                    if blocked_on_lane >= self.num_blocked_per_lane:
                        break
                    if veh_id not in self.blocked_vehicles:
                        traci.vehicle.setSpeed(veh_id, 0)
                        traci.vehicle.setColor(veh_id, (255, 0, 0, 255))
                        self.blocked_vehicles.add(veh_id)
                        blocked_on_lane += 1
            except traci.exceptions.TraCIException:
                continue

        # Keep existing blocks (only those still in simulation)
        active = set(traci.vehicle.getIDList())
        self.blocked_vehicles &= active
        for veh_id in self.blocked_vehicles:
            traci.vehicle.setSpeed(veh_id, 0)

    def _release_lanes(self, lanes):
        """Release blocked vehicles on specific lanes."""
        for lane in lanes:
            try:
                veh_ids = set(traci.lane.getLastStepVehicleIDs(lane))
                to_release = self.blocked_vehicles & veh_ids
                for veh_id in to_release:
                    try:
                        traci.vehicle.setSpeed(veh_id, -1)
                    except traci.exceptions.TraCIException:
                        pass
                self.blocked_vehicles -= to_release
            except traci.exceptions.TraCIException:
                continue


def run():
    scenario = CascadingSpillbackScenario()
    scenario.run()


if __name__ == "__main__":
    run()
