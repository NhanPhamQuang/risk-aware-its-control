# from src.physical.sumo_env import SumoEnv
# from src.twin.state_model import TrafficState
# from src.twin.state_sync import StateSync
# from src.application.risk.risk_manager import RiskManager
# from src.application.control.signal_control import SignalController
#
# def main():
#     print("🚀 Starting Digital Twin...")
#
#     env = SumoEnv("config/simulation.sumocfg")
#     state = TrafficState()
#     sync = StateSync()
#     risk_manager = RiskManager()
#     controller = SignalController()
#
#     env.start()
#     print("✅ SUMO started")
#
#     for step in range(1000):
#         env.step()
#
#         # ===== SYNC STATE =====
#         density, speed, queue = sync.sync()
#         state.update(density, speed, queue)
#
#         # ===== DEBUG: kiểm tra có xe không =====
#         if step % 20 == 0:
#             print(f"\n🧠 Step {step}")
#             print(f"   lanes detected: {len(state.density)}")
#
#         # ===== RISK =====
#         risks = risk_manager.compute(state)
#
#         # ===== DEBUG: in sample risk =====
#         if step % 50 == 0 and len(risks) > 0:
#             sample_lane = list(risks.keys())[0]
#             print(f"   sample risk ({sample_lane}): {risks[sample_lane]}")
#
#         # ===== CONTROL =====
#         actions = controller.decide(state, risks)
#         controller.apply(actions)
#
#     env.close()
#     print("🛑 Simulation ended")
#
# if __name__ == "__main__":
#     main()


# from src.physical.sumo_env import SumoEnv
# from src.twin.state_model import TrafficState
# from src.twin.state_sync import StateSync
# from src.application.risk.risk_manager import RiskManager
# from src.application.control.signal_control import SignalController
#
# def main():
#     print("🚀 Starting Digital Twin System...")
#
#     # ===== INIT =====
#     env = SumoEnv("config/simulation.sumocfg")
#     state = TrafficState()
#     sync = StateSync()
#     risk_manager = RiskManager()
#     controller = SignalController()
#
#     # ===== START SIMULATION =====
#     env.start()
#     print("✅ SUMO started")
#
#     total_steps = 2000
#
#     for step in range(total_steps):
#         env.step()
#
#         # ===== SYNC (Physical → Twin) =====
#         density, speed, queue = sync.sync()
#         state.update(density, speed, queue)
#
#         # ===== BASIC DEBUG =====
#         # if step % 20 == 0:
#         #     print(f"\n🧠 Step {step}")
#         #     print(f"   lanes detected: {len(state.density)}")
#
#         # ===== RISK COMPUTATION =====
#         risks = risk_manager.compute(state)
#
#         # ===== ADVANCED DEBUG =====
#         if step % 10 == 0 and len(risks) > 0:
#             print(f"\n🧠 Step {step}")
#             # worst congestion lane
#             worst_lane = max(risks, key=lambda k: risks[k]["congestion"])
#
#             avg_congestion = sum(r["congestion"] for r in risks.values()) / len(risks)
#             avg_spillback = sum(r["spillback"] for r in risks.values()) / len(risks)
#
#             # print(f"   🔴 worst lane: {worst_lane}")
#             print(f"      congestion: {risks[worst_lane]['congestion']:.2f}")
#             # print(f"      spillback: {risks[worst_lane]['spillback']:.2f}")
#             print(f"🔥 Avg congestion: {avg_congestion:.2f}")
#             # print(f"🚗 Avg spillback: {avg_spillback:.2f}")
#
#         # ===== CONTROL (Application → Physical) =====
#         actions = controller.decide(state, risks)
#         controller.apply(actions)
#
#     # ===== END =====
#     env.close()
#     print("🛑 Simulation ended")
#
#
# if __name__ == "__main__":
#     main()

from src.physical.sumo_env import SumoEnv
from src.twin.state_model import TrafficState
from src.twin.state_sync import StateSync
from src.application.risk.risk_manager import RiskManager
# from src.application.control.signal_control import SignalController
from src.application.control.signal_control import SignalControllerGraphAware

# 🔥 NEW
from src.application.monitoring.db_logger import DBLogger
import uuid
import traci


def main():
    print("🚀 Starting Digital Twin System...")

    # ===== INIT =====
    env = SumoEnv("config/simulation.sumocfg")
    state = TrafficState()
    sync = StateSync()
    risk_manager = RiskManager()
    # controller = SignalController()
    controller = SignalControllerGraphAware()

    # 🔥 DB LOGGER
    logger = DBLogger()
    run_id = str(uuid.uuid4())

    # ===== START SIMULATION =====
    env.start()
    print("✅ SUMO started")

    total_steps = 2000

    for step in range(total_steps):
        env.step()

        # ===== SYNC (Physical → Twin) =====
        density, speed, queue = sync.sync()
        state.update(density, speed, queue)

        # ===== RISK COMPUTATION =====
        risks = risk_manager.compute(state)

        # ===== COMPUTE METRICS =====
        vehicle_count = traci.vehicle.getIDCount()

        avg_congestion = (
            sum(r["congestion"] for r in risks.values()) / len(risks)
            if len(risks) > 0 else 0
        )

        # 🔥 SAVE TO DATABASE
        logger.log(run_id, step, vehicle_count, avg_congestion)

        # ===== DEBUG =====
        if step % 10 == 0 and len(risks) > 0:
            print(f"\n🧠 Step {step}")

            worst_lane = max(risks, key=lambda k: risks[k]["congestion"])

            print(f"      congestion: {risks[worst_lane]['congestion']:.2f}")
            print(f"🔥 Avg congestion: {avg_congestion:.2f}")
            print(f"🚗 Vehicles: {vehicle_count}")

        # ===== CONTROL =====
        actions = controller.decide(state, risks)
        controller.apply(actions)

    # ===== END =====
    logger.close()
    env.close()
    print("🛑 Simulation ended")


if __name__ == "__main__":
    main()