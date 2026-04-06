# # Application evaluation
# # === Evaluation Layer ===
#
# import numpy as np
#
#
# # --- Traffic Metrics ---
#
# def average_speed(speed_dict):
#     """
#     speed_dict: {lane: speed}
#     """
#     if not speed_dict:
#         return 0
#
#     return np.mean(list(speed_dict.values()))
#
#
# def average_queue(queue_dict):
#     if not queue_dict:
#         return 0
#
#     return np.mean(list(queue_dict.values()))
#
#
# def average_density(density_dict):
#     if not density_dict:
#         return 0
#
#     return np.mean(list(density_dict.values()))
#
#
# # --- Risk Metrics ---
#
# def compute_risk_avg(risks):
#     """
#     risks: {lane: {total: ...}}
#     """
#     if not risks:
#         return 0
#
#     return np.mean([r["total"] for r in risks.values()])
#
#
# def compute_risk_max(risks):
#     if not risks:
#         return 0
#
#     return np.max([r["total"] for r in risks.values()])
#
#
# # --- Evaluator (online + offline) ---
#
# class Evaluator:
#     def __init__(self):
#         self.history = []
#
#     def log(self, step, state, risks):
#         """
#         gọi mỗi timestep (online evaluation)
#         """
#         entry = {
#             "step": step,
#             "avg_speed": average_speed(state.speed),
#             "avg_queue": average_queue(state.queue),
#             "avg_density": average_density(state.density),
#             "risk_avg": compute_risk_avg(risks),
#             "risk_max": compute_risk_max(risks)
#         }
#
#         self.history.append(entry)
#
#     def summarize(self):
#         """
#         gọi sau simulation (offline evaluation)
#         """
#         if not self.history:
#             return {}
#
#         avg_speed = np.mean([h["avg_speed"] for h in self.history])
#         avg_queue = np.mean([h["avg_queue"] for h in self.history])
#         avg_density = np.mean([h["avg_density"] for h in self.history])
#         avg_risk = np.mean([h["risk_avg"] for h in self.history])
#         max_risk = np.max([h["risk_max"] for h in self.history])
#
#         return {
#             "avg_speed": avg_speed,
#             "avg_queue": avg_queue,
#             "avg_density": avg_density,
#             "avg_risk": avg_risk,
#             "max_risk": max_risk
#         }
#
#     def get_dataframe(self):
#         import pandas as pd
#         return pd.DataFrame(self.history)

import numpy as np


def average_metric(graph, key):
    values = []

    for _, _, data in graph.G.edges(data=True):
        values.append(data.get(key, 0))

    return np.mean(values) if values else 0


def compute_risk_avg(risks):
    return np.mean([r["total"] for r in risks.values()]) if risks else 0


def compute_risk_max(risks):
    return np.max([r["total"] for r in risks.values()]) if risks else 0


class Evaluator:
    def __init__(self):
        self.history = []

    def log(self, step, graph, risks):
        entry = {
            "step": step,
            "avg_speed": average_metric(graph, "speed"),
            "avg_queue": average_metric(graph, "queue"),
            "avg_density": average_metric(graph, "density"),
            "risk_avg": compute_risk_avg(risks),
            "risk_max": compute_risk_max(risks)
        }

        self.history.append(entry)

    def summarize(self):
        if not self.history:
            return {}

        return {
            "avg_speed": np.mean([h["avg_speed"] for h in self.history]),
            "avg_queue": np.mean([h["avg_queue"] for h in self.history]),
            "avg_density": np.mean([h["avg_density"] for h in self.history]),
            "avg_risk": np.mean([h["risk_avg"] for h in self.history]),
            "max_risk": np.max([h["risk_max"] for h in self.history])
        }