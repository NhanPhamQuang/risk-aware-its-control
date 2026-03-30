from .congestion import congestion_risk
from .instability import instability_risk
from .spillback import spillback_risk

# Bản cũ
class RiskManager:
    def compute(self, state):
        risks = {}

        for lane in state.density:
            Rc = congestion_risk(state.density[lane])
            Ri = instability_risk(state.speed[lane])
            Rs = spillback_risk(state.queue[lane])

            risks[lane] = {
                "congestion": Rc,
                "instability": Ri,
                "spillback": Rs
            }

        return risks

# Bản mới ép cho có congestion
# class RiskManager:
#     def compute(self, state):
#         risks = {}
#
#         for lane in state.density:
#             d = state.density[lane]
#             q = state.queue.get(lane, 0)
#             v = state.speed.get(lane, 0)
#
#             # 🔥 làm nhạy hơn
#             Rc = min(1.0, d / 0.05)
#             Rs = min(1.0, q / 20)
#
#             Ri = 0
#             if v > 0:
#                 Ri = min(1.0, abs(v - 5) / 5)
#
#             risks[lane] = {
#                 "congestion": Rc,
#                 "instability": Ri,
#                 "spillback": Rs
#             }
#
#         return risks