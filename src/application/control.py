# Lane level
# # Application control
# # === Control Layer ===
#
# import traci
#
#
# # --- Phase Policy (chọn hướng ưu tiên) ---
# class PhasePolicy:
#     def select_lane(self, lanes, risks):
#         """
#         chọn lane có pressure cao nhất
#         """
#         best_lane = None
#         best_pressure = -1
#
#         for lane in lanes:
#             Rc = risks[lane]["congestion"]
#             Rs = risks[lane]["spillback"]
#
#             # 🔥 max-pressure (lite version)
#             pressure = Rc + Rs
#
#             if pressure > best_pressure:
#                 best_pressure = pressure
#                 best_lane = lane
#
#         return best_lane, best_pressure
#
#
# # --- Timing Policy (tính thời gian đèn xanh) ---
# class TimingPolicy:
#     def __init__(self, min_green=20, max_green=45, target_congestion=0.8):
#         self.min_green = min_green
#         self.max_green = max_green
#         self.target_congestion = target_congestion
#
#     def compute_green_time(self, pressure):
#         pressure = min(pressure, 1.0)
#
#         green_time = self.min_green + pressure * (self.max_green - self.min_green)
#
#         # 🔥 anti-overflow boost
#         if pressure > self.target_congestion:
#             green_time *= 1.5
#
#         return int(green_time)
#
#
# # --- Signal Controller ---
# class SignalController:
#     def __init__(self):
#         self.phase_policy = PhasePolicy()
#         self.timing_policy = TimingPolicy()
#
#         self.last_switch = {}
#         self.min_switch_interval = 10  # seconds
#
#     def decide(self, state, risks):
#         actions = {}
#
#         # ===== group lane theo traffic light =====
#         tl_groups = {}
#
#         for lane in risks:
#             try:
#                 tl = traci.lane.getTrafficLightID(lane)
#                 if not tl:
#                     continue
#
#                 tl_groups.setdefault(tl, []).append(lane)
#             except:
#                 continue
#
#         # ===== xử lý từng traffic light =====
#         for tl, lanes in tl_groups.items():
#
#             # --- phase selection ---
#             best_lane, pressure = self.phase_policy.select_lane(lanes, risks)
#
#             # --- timing ---
#             green_time = self.timing_policy.compute_green_time(pressure)
#
#             actions[tl] = {
#                 "lane": best_lane,
#                 "pressure": pressure,
#                 "green_time": green_time
#             }
#
#         return actions
#
#     def apply(self, actions):
#         sim_time = traci.simulation.getTime()
#
#         for tl, action in actions.items():
#             try:
#                 green_time = action["green_time"]
#
#                 # ===== tránh switch quá nhanh =====
#                 last = self.last_switch.get(tl, -999)
#                 if sim_time - last < self.min_switch_interval:
#                     continue
#
#                 current_phase = traci.trafficlight.getPhase(tl)
#                 next_phase = (current_phase + 1) % traci.trafficlight.getPhaseNumber(tl)
#
#                 traci.trafficlight.setPhase(tl, next_phase)
#                 traci.trafficlight.setPhaseDuration(tl, green_time)
#
#                 self.last_switch[tl] = sim_time
#
#                 # DEBUG
#                 print(
#                     f"🚦 TL {tl} | phase {current_phase}->{next_phase} | "
#                     f"pressure={action['pressure']:.2f} | green={green_time}"
#                 )
#
#             except Exception:
#                 continue


# Graph level
# import traci
#
#
# class SignalController:
#     def __init__(self):
#         self.last_switch = {}
#         self.min_switch_interval = 10
#
#     def compute_pressure(self, graph, u, v, data):
#         Q_up = data["queue"]
#
#         Q_down = 0
#         for _, nxt, d2 in graph.G.out_edges(v, data=True):
#             Q_down += d2["queue"]
#
#         pressure = Q_up - Q_down
#
#         if data.get("blocked", False):
#             pressure -= 100
#
#         return pressure
#
#     def decide(self, graph):
#         actions = {}
#
#         for tl in traci.trafficlight.getIDList():
#
#             lanes = traci.trafficlight.getControlledLanes(tl)
#
#             best_pressure = -999
#             best_edge = None
#
#             for lane in lanes:
#                 for u, v, data in graph.G.edges(data=True):
#                     if data["id"] == lane:
#                         pressure = self.compute_pressure(graph, u, v, data)
#
#                         if pressure > best_pressure:
#                             best_pressure = pressure
#                             best_edge = (u, v)
#
#             if best_edge:
#                 actions[tl] = {
#                     "pressure": best_pressure,
#                     "green_time": int(20 + min(best_pressure, 1) * 20)
#                 }
#
#         return actions
#
#     def apply(self, actions):
#         sim_time = traci.simulation.getTime()
#
#         for tl, action in actions.items():
#
#             last = self.last_switch.get(tl, -999)
#             if sim_time - last < self.min_switch_interval:
#                 continue
#
#             try:
#                 current = traci.trafficlight.getPhase(tl)
#                 next_phase = (current + 1) % traci.trafficlight.getPhaseNumber(tl)
#
#                 traci.trafficlight.setPhase(tl, next_phase)
#                 traci.trafficlight.setPhaseDuration(tl, action["green_time"])
#
#                 self.last_switch[tl] = sim_time
#
#             except:
#                 continue

# Xả khi nào hết thì thôi
import traci


class SignalController:
    def __init__(self):
        self.last_switch = {}
        self.min_switch_interval = 10
        self.max_green = 60
        self.keep_green_threshold = 8   # > cái này thì giữ xanh
        self.release_threshold = 3      # < cái này thì nhả

        # cache mapping
        self.tl_phases = {}     # tl -> phases
        self.lane_phase_map = {}  # tl -> lane -> phase index

    # ========================
    # PRESSURE
    # ========================
    def compute_pressure(self, graph, u, v, data):
        Q_up = data["queue"]

        Q_down = 0
        for _, nxt, d2 in graph.G.out_edges(v, data=True):
            Q_down += d2["queue"]

        pressure = Q_up - Q_down

        if data.get("blocked", False):
            pressure -= 100

        return pressure

    # ========================
    # BUILD PHASE MAP (QUAN TRỌNG)
    # ========================
    def build_phase_map(self, tl):
        if tl in self.lane_phase_map:
            return

        logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl)[0]
        phases = logic.phases
        lanes = traci.trafficlight.getControlledLanes(tl)

        self.tl_phases[tl] = phases
        self.lane_phase_map[tl] = {}

        for i, phase in enumerate(phases):
            state = phase.state  # ví dụ "GrGr"

            for idx, signal in enumerate(state):
                if signal in ['G', 'g']:  # lane được đi
                    lane = lanes[idx]
                    if lane not in self.lane_phase_map[tl]:
                        self.lane_phase_map[tl][lane] = []
                    self.lane_phase_map[tl][lane].append(i)

    # ========================
    # DECIDE
    # ========================
    def decide(self, graph):
        actions = {}

        for tl in traci.trafficlight.getIDList():

            self.build_phase_map(tl)

            lanes = traci.trafficlight.getControlledLanes(tl)

            best_pressure = -9999
            best_lane = None

            for lane in lanes:
                for u, v, data in graph.G.edges(data=True):
                    if data["id"] == lane:
                        pressure = self.compute_pressure(graph, u, v, data)

                        if pressure > best_pressure:
                            best_pressure = pressure
                            best_lane = lane

            if best_lane:
                candidate_phases = self.lane_phase_map[tl].get(best_lane, [])

                if not candidate_phases:
                    continue

                actions[tl] = {
                    "pressure": best_pressure,
                    "lane": best_lane,
                    "phases": candidate_phases
                }

        return actions

    # ========================
    # APPLY (CORE LOGIC)
    # ========================
    def apply(self, actions, graph):
        sim_time = traci.simulation.getTime()

        for tl, action in actions.items():

            current_phase = traci.trafficlight.getPhase(tl)
            last = self.last_switch.get(tl, -999)

            lane = action["lane"]
            candidate_phases = action["phases"]

            # 👉 lấy queue của lane đang target
            queue = traci.lane.getLastStepHaltingNumber(lane)

            # ========================
            # CASE 1: đang đúng phase → giữ xanh
            # ========================
            if current_phase in candidate_phases:
                if queue > self.keep_green_threshold:
                    traci.trafficlight.setPhaseDuration(tl, 5)
                    continue

                if queue > self.release_threshold:
                    traci.trafficlight.setPhaseDuration(tl, 3)
                    continue

            # ========================
            # CASE 2: cần switch phase
            # ========================
            if sim_time - last < self.min_switch_interval:
                continue

            try:
                target_phase = candidate_phases[0]

                traci.trafficlight.setPhase(tl, target_phase)
                traci.trafficlight.setPhaseDuration(
                    tl,
                    max(5, min(self.max_green, int(10 + action["pressure"])))
                )

                self.last_switch[tl] = sim_time

            except Exception as e:
                print(f"[ERROR] {tl}: {e}")
                continue