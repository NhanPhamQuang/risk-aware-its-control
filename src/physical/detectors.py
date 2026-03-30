# import traci
#
# def get_lane_data():
#     lanes = traci.lane.getIDList()
#
#     data = {}
#
#     for lane in lanes:
#         veh = traci.lane.getLastStepVehicleNumber(lane)
#         length = traci.lane.getLength(lane)
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

def get_lane_data():
    lanes = traci.lane.getIDList()

    data = {}

    for lane in lanes:

        # 🔥 FIX 1: bỏ internal/junction lanes
        if lane.startswith(":"):
            continue

        length = traci.lane.getLength(lane)

        # 🔥 FIX 2: bỏ lane quá ngắn (noise rất lớn)
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