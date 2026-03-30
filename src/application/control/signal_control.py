# -------------------------------------------------------------
# Bản cũ
# -------------------------------------------------------------
# import traci
#
# class SignalController:
#
#     def decide(self, state, risks):
#         actions = {}
#         tls_ids = traci.trafficlight.getIDList()
#
#         for tls in tls_ids:
#             for lane, r in risks.items():
#                 if r["spillback"] > 0.8:
#                     actions[tls] = 2
#                 elif r["congestion"] > 0.8:
#                     actions[tls] = 1
#                 else:
#                     actions[tls] = 0
#
#         return actions
#
#     def apply(self, actions):
#         for tls, phase in actions.items():
#             traci.trafficlight.setPhase(tls, phase)

# -------------------------------------------------------------
# làm đèn “ngu” hơn
# actions[tls] = 0   # giữ 1 phase
# → 3 hướng bị block → kẹt ngay
# -------------------------------------------------------------
# import traci
#
# class SignalController:
#
#     def decide(self, state, risks):
#         actions = {}
#         tls_ids = traci.trafficlight.getIDList()
#
#         for tls in tls_ids:
#             # 🔥 ép giữ phase 0 → chặn các hướng khác
#             actions[tls] = 0
#
#         return actions
#
#     def apply(self, actions):
#         for tls, phase in actions.items():
#             traci.trafficlight.setPhase(tls, phase)

# -------------------------------------------------------------
# rule-based điều khiển đèn - bản này chạy được rồi
# -------------------------------------------------------------
# import traci
#
# class SignalController:
#     def __init__(self):
#         # thời gian xanh tối thiểu / tối đa
#         self.min_green = 10
#         self.max_green = 60
#
#     def decide(self, state, risks):
#         """
#         Max-pressure lite:
#         pressure = congestion + queue
#         """
#
#         actions = {}
#
#         # ===== group lanes theo traffic light =====
#         tl_groups = {}
#
#         for lane in risks:
#             try:
#                 tl = traci.lane.getTrafficLightID(lane)
#                 if not tl:
#                     continue
#
#                 if tl not in tl_groups:
#                     tl_groups[tl] = []
#
#                 tl_groups[tl].append(lane)
#
#             except:
#                 continue
#
#         # ===== compute action cho từng traffic light =====
#         for tl, lanes in tl_groups.items():
#
#             best_lane = None
#             best_score = -1
#
#             for lane in lanes:
#                 Rc = risks[lane]["congestion"]
#                 Rq = risks[lane]["spillback"]
#
#                 # 🔥 pressure
#                 score = Rc + Rq
#
#                 if score > best_score:
#                     best_score = score
#                     best_lane = lane
#
#             # map score → green time
#             score = min(best_score, 1.0)
#             green_time = self.min_green + score * (self.max_green - self.min_green)
#
#             actions[tl] = {
#                 "lane": best_lane,
#                 "green_time": green_time
#             }
#
#         return actions
#
#     def apply(self, actions):
#         """
#         Apply control xuống SUMO
#         """
#
#         for tl, action in actions.items():
#             try:
#                 green_time = int(action["green_time"])
#
#                 # 🔥 giữ phase hiện tại nhưng kéo dài thời gian xanh
#                 traci.trafficlight.setPhaseDuration(tl, green_time)
#
#             except:
#                 continue

# -------------------------------------------------------------
# rule-based điều khiển đèn - max pressure
# -------------------------------------------------------------
import traci


class SignalController:
    def __init__(self):
        self.min_green = 20
        self.max_green = 45
        self.target_congestion = 0.8

        # tránh đổi phase liên tục (rất quan trọng)
        self.last_switch = {}
        self.min_switch_interval = 10  # seconds

    def decide(self, state, risks):
        actions = {}

        # ===== group lane theo traffic light =====
        tl_groups = {}

        for lane in risks:
            try:
                tl = traci.lane.getTrafficLightID(lane)
                if not tl:
                    continue

                tl_groups.setdefault(tl, []).append(lane)
            except:
                continue

        # ===== xử lý từng traffic light =====
        for tl, lanes in tl_groups.items():

            # ===== compute pressure =====
            best_lane = None
            best_pressure = -1

            for lane in lanes:
                Rc = risks[lane]["congestion"]
                Rq = risks[lane]["spillback"]

                # 🔥 max-pressure (lite nhưng đúng bản chất)
                pressure = Rc + Rq

                if pressure > best_pressure:
                    best_pressure = pressure
                    best_lane = lane

            # ===== compute green time =====
            pressure = min(best_pressure, 1.0)
            green_time = self.min_green + pressure * (self.max_green - self.min_green)

            # ===== anti-overflow control (<0.8) =====
            if best_pressure > self.target_congestion:
                green_time *= 1.5  # 🔥 boost để xả nhanh

            actions[tl] = {
                "lane": best_lane,
                "pressure": best_pressure,
                "green_time": green_time
            }

        return actions

    def apply(self, actions):
        sim_time = traci.simulation.getTime()

        for tl, action in actions.items():
            try:
                green_time = int(action["green_time"])

                # ===== tránh switch quá nhanh =====
                last = self.last_switch.get(tl, -999)

                if sim_time - last < self.min_switch_interval:
                    continue

                # ===== lấy phase hiện tại =====
                current_phase = traci.trafficlight.getPhase(tl)

                # 🔥 SWITCH PHASE (điểm nâng cấp thật)
                next_phase = (current_phase + 1) % traci.trafficlight.getPhaseNumber(tl)

                traci.trafficlight.setPhase(tl, next_phase)
                traci.trafficlight.setPhaseDuration(tl, green_time)

                self.last_switch[tl] = sim_time

                # ===== DEBUG =====
                print(
                    f"🚦 TL {tl} | phase {current_phase}->{next_phase} | "
                    f"pressure={action['pressure']:.2f} | green={green_time}"
                )

            except Exception as e:
                continue


# -------------------------------------------------------------
# Graph Aware
# -------------------------------------------------------------
import traci


class SignalControllerGraphAware:
    def __init__(self):
        self.min_green = 8
        self.max_green = 50
        self.target_congestion = 0.8

        self.last_switch = {}
        self.min_switch_interval = 10

    def decide(self, state, risks):
        actions = {}

        # ===== group lanes theo traffic light =====
        tl_groups = {}

        for lane in risks:
            try:
                tl = traci.lane.getTrafficLightID(lane)
                if not tl:
                    continue
                tl_groups.setdefault(tl, []).append(lane)
            except:
                continue

        # ===== compute pressure chuẩn =====
        for tl, lanes in tl_groups.items():

            best_lane = None
            best_pressure = -999

            for lane in lanes:
                try:
                    q_in = state.queue[lane]

                    # 🔥 downstream lanes
                    links = traci.lane.getLinks(lane)

                    q_out = 0
                    count = 0

                    for link in links:
                        next_lane = link[0]
                        if next_lane in state.queue:
                            q_out += state.queue[next_lane]
                            count += 1

                    if count > 0:
                        q_out /= count  # average downstream queue

                    # 🔥 max-pressure chuẩn
                    pressure = q_in - q_out

                except:
                    pressure = 0

                if pressure > best_pressure:
                    best_pressure = pressure
                    best_lane = lane

            # ===== scale green time =====
            pressure_norm = max(0, min(best_pressure / 10, 1))  # normalize

            green_time = self.min_green + pressure_norm * (self.max_green - self.min_green)

            # 🔥 anti congestion
            if best_pressure > 5:
                green_time *= 1.5

            actions[tl] = {
                "lane": best_lane,
                "pressure": best_pressure,
                "green_time": green_time
            }

        return actions

    def apply(self, actions):
        sim_time = traci.simulation.getTime()

        for tl, action in actions.items():
            try:
                last = self.last_switch.get(tl, -999)

                if sim_time - last < self.min_switch_interval:
                    continue

                current_phase = traci.trafficlight.getPhase(tl)
                num_phases = traci.trafficlight.getPhaseNumber(tl)

                next_phase = (current_phase + 1) % num_phases

                traci.trafficlight.setPhase(tl, next_phase)
                traci.trafficlight.setPhaseDuration(tl, int(action["green_time"]))

                self.last_switch[tl] = sim_time

                print(
                    f"🚦 TL {tl} | P={action['pressure']:.2f} | "
                    f"lane={action['lane']} | green={action['green_time']:.1f}"
                )

            except:
                continue