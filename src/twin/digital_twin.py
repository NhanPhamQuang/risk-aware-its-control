# from src.physical.environment import get_lane_data
# # Twin layer
# # === Digital Twin Layer ===
#
# # --- Feature Extractor ---
# def compute_density(vehicle_count, length):
#     return vehicle_count / length if length > 0 else 0
#
#
# # --- State Model ---
# class TrafficState:
#     def __init__(self):
#         self.density = {}
#         self.speed = {}
#         self.queue = {}
#
#     def update(self, density, speed, queue):
#         self.density = density
#         self.speed = speed
#         self.queue = queue
#
#     def as_dict(self):
#         return {
#             "density": self.density,
#             "speed": self.speed,
#             "queue": self.queue
#         }
#
#
# # --- State Sync (Physical → Twin) ---
# # ⚠️ assume get_lane_data() đã có từ cell trước
# class StateSync:
#
#     def sync(self):
#         raw = get_lane_data()
#
#         density = {}
#         speed = {}
#         queue = {}
#
#         for lane, d in raw.items():
#             density[lane] = compute_density(d["vehicle_count"], d["length"])
#             speed[lane] = d["speed"]
#             queue[lane] = d["queue"]
#
#         return density, speed, queue
#
#
# # --- State Store (logging + phục vụ evaluation) ---
# class StateStore:
#     def __init__(self):
#         self.history = []
#
#     def add(self, step, state):
#         self.history.append({
#             "step": step,
#             "density": state.density.copy(),
#             "speed": state.speed.copy(),
#             "queue": state.queue.copy()
#         })
#
#     def get_dataframe(self):
#         import pandas as pd
#         return pd.DataFrame(self.history)

from src.physical.environment import get_lane_data


# --- Feature ---
def compute_density(vehicle_count, length):
    return vehicle_count / length if length > 0 else 0


# 🔥 GRAPH-BASED STATE
class TrafficGraph:
    def __init__(self, G):
        self.G = G

    def update(self, density, speed, queue):
        for u, v, data in self.G.edges(data=True):
            lane = data["id"]

            data["density"] = density.get(lane, 0)
            data["speed"] = speed.get(lane, 0)
            data["queue"] = queue.get(lane, 0)


# --- Sync ---
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


# --- Store ---
class StateStore:
    def __init__(self):
        self.history = []

    def add(self, step, graph):
        snapshot = {}

        for _, _, data in graph.G.edges(data=True):
            lane = data["id"]
            snapshot[lane] = {
                "density": data["density"],
                "speed": data["speed"],
                "queue": data["queue"]
            }

        self.history.append({
            "step": step,
            "state": snapshot
        })