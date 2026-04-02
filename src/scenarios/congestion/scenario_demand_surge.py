"""
Scenario 1: Demand Surge
========================
Simulates a sudden traffic demand spike (e.g., rush hour, event dispersal).
Injects large bursts of vehicles at intervals to overwhelm lane capacity.

Congestion mechanism:
  - Arrival rate >> departure rate
  - Density increases -> congestion_risk(density) = density / jam_density rises
  - Vehicles queue at junctions waiting for gaps
"""

import traci
import random
from src.scenarios.congestion.base_scenario import BaseScenario


class DemandSurgeScenario(BaseScenario):

    def __init__(self, total_steps=None, burst_size=8, burst_interval=10, surge_start=100, surge_end=800):
        super().__init__(total_steps=total_steps)
        self.burst_size = burst_size          # vehicles per burst
        self.burst_interval = burst_interval  # steps between bursts
        self.surge_start = surge_start        # when surge begins
        self.surge_end = surge_end            # when surge ends
        self.veh_counter = 10000              # unique vehicle ID counter

        # Available edges for route generation
        self.edges = ["-100#0", "-100#1", "-101#0", "-101#1",
                      "100#0", "100#1", "101#0", "101#1"]

    def get_name(self):
        return "demand_surge"

    def get_description(self):
        return (
            f"Inject {self.burst_size} vehicles every {self.burst_interval} steps "
            f"from step {self.surge_start} to {self.surge_end}"
        )

    def _make_route(self):
        """Generate a random valid 2-edge route through the network."""
        # Pick a random origin edge
        origin = random.choice(self.edges)
        # Get reachable edges from connections
        try:
            origin_lane = origin + "_0"
            links = traci.lane.getLinks(origin_lane)
            if links:
                dest_lane = random.choice(links)[0]
                dest_edge = traci.lane.getEdgeID(dest_lane)
                return [origin, dest_edge]
        except Exception:
            pass
        return None

    def inject_perturbation(self, step):
        """Inject vehicle bursts during surge window."""
        if step < self.surge_start or step > self.surge_end:
            return
        if step % self.burst_interval != 0:
            return

        injected = 0
        for _ in range(self.burst_size):
            route = self._make_route()
            if route is None:
                continue

            veh_id = f"surge_{self.veh_counter}"
            route_id = f"route_surge_{self.veh_counter}"
            self.veh_counter += 1

            try:
                traci.route.add(route_id, route)
                traci.vehicle.add(veh_id, route_id)
                injected += 1
            except traci.exceptions.TraCIException:
                continue

        if injected > 0 and step % 100 == 0:
            print(f"  [SURGE] Step {step}: injected {injected} vehicles")


def run():
    scenario = DemandSurgeScenario()
    scenario.run()


if __name__ == "__main__":
    run()
