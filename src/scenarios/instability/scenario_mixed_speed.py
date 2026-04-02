"""
Scenario 2: Mixed Speed Fleet
==============================
Injects slow vehicles (simulating trucks, disabled vehicles) among normal
fast traffic. The speed differential between slow (~5 m/s) and fast (~28 m/s)
vehicles on the same lane creates high speed variance.

Instability mechanism:
  - Slow vehicles create moving bottlenecks
  - Fast vehicles approach quickly and must brake suddenly
  - Accordion effect: vehicles behind alternate between fast/slow
  - Same lane has vehicles at 5 m/s and 25 m/s simultaneously -> high CV
"""

import traci
import random
from src.scenarios.instability.base_scenario import InstabilityBaseScenario


class MixedSpeedScenario(InstabilityBaseScenario):

    def __init__(self, total_steps=None, slow_speed=3.0, inject_interval=15,
                 start_step=100, end_step=900):
        super().__init__(total_steps=total_steps)
        self.slow_speed = slow_speed            # m/s (~11 km/h, truck speed)
        self.inject_interval = inject_interval  # steps between slow vehicle injections
        self.start_step = start_step
        self.end_step = end_step
        self.veh_counter = 30000
        self.slow_vehicles = set()

        self.edges = ["-100#0", "-100#1", "-101#0", "-101#1",
                      "100#0", "100#1", "101#0", "101#1"]

    def get_name(self):
        return "mixed_speed_fleet"

    def get_description(self):
        return (
            f"Inject slow vehicles ({self.slow_speed} m/s) every {self.inject_interval} steps "
            f"among normal traffic (step {self.start_step}-{self.end_step})"
        )

    def inject_perturbation(self, step):
        """Inject slow vehicles into the network."""
        if step < self.start_step or step > self.end_step:
            return

        if step % self.inject_interval != 0:
            return

        self._inject_slow_vehicle()
        self._enforce_slow_speeds()

    def _inject_slow_vehicle(self):
        """Add a slow vehicle with a random route."""
        origin = random.choice(self.edges)
        try:
            links = traci.lane.getLinks(origin + "_0")
            if not links:
                return
            dest_lane = random.choice(links)[0]
            dest_edge = traci.lane.getEdgeID(dest_lane)

            veh_id = f"slow_{self.veh_counter}"
            route_id = f"route_slow_{self.veh_counter}"
            self.veh_counter += 1

            traci.route.add(route_id, [origin, dest_edge])
            traci.vehicle.add(veh_id, route_id)
            traci.vehicle.setMaxSpeed(veh_id, self.slow_speed)
            traci.vehicle.setColor(veh_id, (0, 0, 255, 255))  # blue = slow
            self.slow_vehicles.add(veh_id)

        except traci.exceptions.TraCIException:
            pass

    def _enforce_slow_speeds(self):
        """Ensure slow vehicles stay slow (remove departed ones)."""
        active = set(traci.vehicle.getIDList())
        self.slow_vehicles &= active
        for veh_id in self.slow_vehicles:
            traci.vehicle.setMaxSpeed(veh_id, self.slow_speed)


def run():
    scenario = MixedSpeedScenario()
    scenario.run()


if __name__ == "__main__":
    run()
