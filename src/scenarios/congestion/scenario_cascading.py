"""
Scenario 4: Cascading Congestion (Combined Stress)
===================================================
Combines multiple congestion triggers simultaneously:
  1. High demand surge (more vehicles)
  2. Incident blockage on a critical lane
  3. Speed reduction on adjacent lane

This creates a cascading failure where congestion propagates
across the entire network - the most severe scenario.

Congestion mechanism:
  - Demand surge increases overall density
  - Incident blocks a key lane, forcing rerouting
  - Speed reduction on adjacent lane creates secondary bottleneck
  - Vehicles have nowhere to go -> network-wide gridlock
  - All risk metrics spike: congestion, spillback, instability
"""

import traci
import random
from src.scenarios.congestion.base_scenario import BaseScenario


class CascadingCongestionScenario(BaseScenario):

    def __init__(self, total_steps=None):
        super().__init__(total_steps=total_steps)

        # Phase 1: Demand surge parameters
        self.surge_start = 100
        self.surge_end = 1200
        self.burst_size = 6
        self.burst_interval = 8
        self.veh_counter = 20000

        # Phase 2: Incident parameters
        self.incident_start = 300
        self.incident_end = 900
        self.incident_lane = "100#0_0"
        self.num_blocked = 3
        self.blocked_vehicles = set()

        # Phase 3: Bottleneck parameters
        self.bottleneck_start = 400
        self.bottleneck_end = 1000
        self.bottleneck_lane = "-100#1_0"
        self.reduced_speed = 1.5   # m/s (~5.4 km/h)
        self.original_speed = None

        # Network edges
        self.edges = ["-100#0", "-100#1", "-101#0", "-101#1",
                      "100#0", "100#1", "101#0", "101#1"]

    def get_name(self):
        return "cascading_congestion"

    def get_description(self):
        return (
            "Combined stress: demand surge (step 100-1200) + "
            "incident on 100#0_0 (step 300-900) + "
            "bottleneck on -100#1_0 (step 400-1000)"
        )

    def inject_perturbation(self, step):
        """Apply all three perturbation types in sequence."""
        self._demand_surge(step)
        self._incident(step)
        self._bottleneck(step)

    # ---- Phase 1: Demand Surge ----
    def _demand_surge(self, step):
        if step < self.surge_start or step > self.surge_end:
            return
        if step % self.burst_interval != 0:
            return

        injected = 0
        for _ in range(self.burst_size):
            origin = random.choice(self.edges)
            try:
                links = traci.lane.getLinks(origin + "_0")
                if not links:
                    continue
                dest_lane = random.choice(links)[0]
                dest_edge = traci.lane.getEdgeID(dest_lane)

                veh_id = f"cascade_{self.veh_counter}"
                route_id = f"route_cascade_{self.veh_counter}"
                self.veh_counter += 1

                traci.route.add(route_id, [origin, dest_edge])
                traci.vehicle.add(veh_id, route_id)
                injected += 1
            except traci.exceptions.TraCIException:
                continue

    # ---- Phase 2: Incident ----
    def _incident(self, step):
        if step == self.incident_start:
            print(f"\n  [CASCADE-INCIDENT] Blocking vehicles on {self.incident_lane}")

        if self.incident_start <= step <= self.incident_end:
            # Find and block vehicles
            try:
                vehs = traci.lane.getLastStepVehicleIDs(self.incident_lane)
                for veh_id in vehs:
                    if veh_id not in self.blocked_vehicles and len(self.blocked_vehicles) < self.num_blocked:
                        traci.vehicle.setSpeed(veh_id, 0)
                        traci.vehicle.setColor(veh_id, (255, 0, 0, 255))
                        self.blocked_vehicles.add(veh_id)
            except traci.exceptions.TraCIException:
                pass

            # Maintain existing blocks (only those still in simulation)
            active = set(traci.vehicle.getIDList())
            self.blocked_vehicles &= active
            for veh_id in self.blocked_vehicles:
                traci.vehicle.setSpeed(veh_id, 0)

        if step == self.incident_end + 1:
            active = set(traci.vehicle.getIDList())
            for veh_id in self.blocked_vehicles & active:
                traci.vehicle.setSpeed(veh_id, -1)
            self.blocked_vehicles.clear()
            print(f"  [CASCADE-INCIDENT] Cleared")

    # ---- Phase 3: Bottleneck ----
    def _bottleneck(self, step):
        if step == self.bottleneck_start:
            try:
                self.original_speed = traci.lane.getMaxSpeed(self.bottleneck_lane)
                traci.lane.setMaxSpeed(self.bottleneck_lane, self.reduced_speed)
                print(f"  [CASCADE-BOTTLENECK] {self.bottleneck_lane}: "
                      f"{self.original_speed:.1f} -> {self.reduced_speed} m/s")
            except traci.exceptions.TraCIException:
                pass

        if step == self.bottleneck_end + 1 and self.original_speed is not None:
            try:
                traci.lane.setMaxSpeed(self.bottleneck_lane, self.original_speed)
                print(f"  [CASCADE-BOTTLENECK] Restored {self.bottleneck_lane}")
            except traci.exceptions.TraCIException:
                pass


def run():
    scenario = CascadingCongestionScenario()
    scenario.run()


if __name__ == "__main__":
    run()
