"""
Scenario 3: Queue Saturation via Demand Flood
==============================================
Floods specific approach lanes with heavy targeted demand so queues
exceed lane storage capacity, causing spillback at junctions.

Spillback mechanism:
  - Massive vehicle injection targeted at J2 approach lanes
  - Arrival rate far exceeds junction clearance rate
  - Queue grows until it fills the entire lane (~100m)
  - Overflow blocks upstream junction, causing chain spillback
  - Rs = queue / lane_length spikes above 1.0
"""

import traci
import random
from src.scenarios.spillback.base_scenario import SpillbackBaseScenario


class DemandFloodScenario(SpillbackBaseScenario):

    def __init__(self, total_steps=None, burst_size=10, burst_interval=8,
                 start_step=100, end_step=900):
        super().__init__(total_steps=total_steps)
        self.burst_size = burst_size
        self.burst_interval = burst_interval
        self.start_step = start_step
        self.end_step = end_step
        self.veh_counter = 40000

        # Target routes that go THROUGH junction 2
        # These create maximum queue pressure at J2
        self.target_routes = [
            ["-100#1", "100#1"],      # west -> east through J2
            ["-100#1", "-101#0"],     # west -> south through J2
            ["-100#1", "101#1"],      # west -> north through J2
            ["100#0", "-100#0"],      # east -> west through J2
            ["100#0", "101#1"],       # east -> north through J2
            ["101#0", "-101#0"],      # north -> south through J2
            ["101#0", "100#1"],       # north -> east through J2
            ["-101#1", "-100#0"],     # south -> west through J2
        ]

    def get_name(self):
        return "demand_flood_spillback"

    def get_description(self):
        return (
            f"Inject {self.burst_size} vehicles every {self.burst_interval} steps "
            f"targeting J2 (step {self.start_step}-{self.end_step})"
        )

    def inject_perturbation(self, step):
        if step < self.start_step or step > self.end_step:
            return
        if step % self.burst_interval != 0:
            return

        self._inject_burst()

    def _inject_burst(self):
        """Inject vehicles with routes through J2."""
        injected = 0
        for _ in range(self.burst_size):
            route_edges = random.choice(self.target_routes)
            veh_id = f"flood_{self.veh_counter}"
            route_id = f"route_flood_{self.veh_counter}"
            self.veh_counter += 1

            try:
                traci.route.add(route_id, route_edges)
                traci.vehicle.add(veh_id, route_id)
                injected += 1
            except traci.exceptions.TraCIException:
                continue


def run():
    scenario = DemandFloodScenario()
    scenario.run()


if __name__ == "__main__":
    run()
