# # Physical layer
# # === Physical Layer: SUMO Env + Detector ===
#
# import traci
#
#
# class SumoEnv:
#     def __init__(self, config_path):
#         self.config_path = config_path
#
#     def start(self):
#         print("Starting SUMO GUI...")
#         traci.start([
#             "sumo-gui",
#             "-c", self.config_path,
#             "--start",  # 🔥 auto play
#             "--quit-on-end"
#         ])
#
#     def step(self):
#         traci.simulationStep()
#
#     def close(self):
#         traci.close()
#
#
# # === Detector ===
# def get_lane_data():
#     lanes = traci.lane.getIDList()
#     data = {}
#
#     for lane in lanes:
#
#         # 🔥 FIX 1: bỏ internal/junction lanes
#         if lane.startswith(":"):
#             continue
#
#         length = traci.lane.getLength(lane)
#
#         # 🔥 FIX 2: bỏ lane quá ngắn (noise lớn)
#         if length < 20:
#             continue
#
#         veh = traci.lane.getLastStepVehicleNumber(lane)
#         speed = traci.lane.getLastStepMeanSpeed(lane)
#         halt = traci.lane.getLastStepHaltingNumber(lane)
#
#         data[lane] = {
#             "vehicle_count": veh,
#             "length": length,
#             "speed": speed,
#             "queue": halt
#         }
#
#     return data

import traci


class SumoEnv:
    def __init__(self, config_path):
        self.config_path = config_path

    def start(self):
        print("🚀 Starting SUMO GUI...")
        traci.start([
            "sumo-gui",
            "-c", self.config_path,
            "--start",
            "--quit-on-end"
        ])

    def step(self):
        traci.simulationStep()

    def close(self):
        traci.close()


# === Detector ===
def get_lane_data():
    lanes = traci.lane.getIDList()
    data = {}

    for lane in lanes:

        if lane.startswith(":"):
            continue

        length = traci.lane.getLength(lane)
        if length < 20:
            continue

        veh = traci.lane.getLastStepVehicleNumber(lane)
        speed = traci.lane.getLastStepMeanSpeed(lane)
        halt = traci.lane.getLastStepHaltingNumber(lane)

        data[lane] = {
            "vehicle_count": veh,
            "length": length,
            "speed": speed,
            "queue": halt
        }

    return data