from src.physical.detectors import get_lane_data
from src.twin.feature_extractor import compute_density

class StateSync:

    def sync(self):
        raw = get_lane_data()

        density = {}
        speed = {}
        queue = {}

        for lane, d in raw.items():
            density[lane] = compute_density(d["vehicle_count"], d["length"])
            speed[lane] = d["speed"]
            queue[lane] = d["queue"]

        return density, speed, queue