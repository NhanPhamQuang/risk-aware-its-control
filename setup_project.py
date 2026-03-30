import os


# ==============================
# Helper functions
# ==============================
def create_dir(path):
    os.makedirs(path, exist_ok=True)


def create_file(path, content=""):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ==============================
# Directory structure
# ==============================
dirs = [
    "data",
    "network",
    "demand",
    "config",
    "outputs/logs",
    "outputs/metrics",
    "outputs/plots",
    "experiments",
    "notebooks",

    "src/physical",
    "src/twin",
    "src/application/risk",
    "src/application/control",
    "src/application/evaluation",
    "src/application/monitoring",
    "src/utils",
    "src/config"
]

for d in dirs:
    create_dir(d)

# ==============================
# Files content
# ==============================

# main.py
create_file("main.py", """\
from src.physical.sumo_env import SumoEnv
from src.twin.state_model import TrafficState
from src.twin.state_sync import StateSync
from src.application.risk.risk_manager import RiskManager
from src.application.control.signal_control import SignalController

def main():
    env = SumoEnv("config/simulation.sumocfg")
    state = TrafficState()
    sync = StateSync()
    risk_manager = RiskManager()
    controller = SignalController()

    env.start()

    for step in range(1000):
        env.step()

        raw_data = sync.read_from_sumo()
        state.update(raw_data)

        risk = risk_manager.compute(state)
        action = controller.decide(state, risk)

        controller.apply(action)

    env.close()

if __name__ == "__main__":
    main()
""")

# ==============================
# Physical Layer
# ==============================

create_file("src/physical/sumo_env.py", """\
import traci

class SumoEnv:
    def __init__(self, config):
        self.config = config

    def start(self):
        traci.start(["sumo-gui", "-c", self.config])

    def step(self):
        traci.simulationStep()

    def close(self):
        traci.close()
""")

create_file("src/physical/traffic_env.py", "# abstraction layer\n")
create_file("src/physical/detectors.py", "# get data from SUMO\n")

# ==============================
# Digital Twin Layer
# ==============================

create_file("src/twin/state_model.py", """\
class TrafficState:
    def __init__(self):
        self.density = {}
        self.speed = {}
        self.queue = {}

    def update(self, data):
        self.density = data.get("density", {})
        self.speed = data.get("speed", {})
        self.queue = data.get("queue", {})
""")

create_file("src/twin/state_sync.py", """\
import traci

class StateSync:
    def read_from_sumo(self):
        # TODO: replace with real extraction
        return {
            "density": {},
            "speed": {},
            "queue": {}
        }
""")

create_file("src/twin/feature_extractor.py", """\
def compute_density(vehicle_count, length):
    return vehicle_count / length if length > 0 else 0
""")

create_file("src/twin/state_store.py", "# store history state\n")

# ==============================
# Risk Module
# ==============================

create_file("src/application/risk/congestion.py", """\
def congestion_risk(density, jam_density=1.0):
    return density / jam_density if jam_density > 0 else 0
""")

create_file("src/application/risk/instability.py", """\
import numpy as np

def instability_risk(speeds):
    if len(speeds) == 0:
        return 0
    return np.std(speeds) / (np.mean(speeds) + 1e-5)
""")

create_file("src/application/risk/spillback.py", """\
def spillback_risk(queue_length, lane_length):
    return queue_length / lane_length if lane_length > 0 else 0
""")

create_file("src/application/risk/risk_manager.py", """\
from .congestion import congestion_risk
from .instability import instability_risk
from .spillback import spillback_risk

class RiskManager:
    def compute(self, state):
        risks = {}

        for lane in state.density:
            Rc = congestion_risk(state.density[lane])
            Rs = spillback_risk(state.queue.get(lane, 0), 100)

            risks[lane] = {
                "congestion": Rc,
                "spillback": Rs
            }

        return risks
""")

# ==============================
# Control Module
# ==============================

create_file("src/application/control/signal_control.py", """\
import traci

class SignalController:
    def decide(self, state, risk):
        # simple rule-based
        return {"action": "adjust"}

    def apply(self, action):
        # TODO: implement traffic light control
        pass
""")

create_file("src/application/control/phase_policy.py", "# phase logic\n")
create_file("src/application/control/timing_policy.py", "# timing logic\n")

# ==============================
# Evaluation
# ==============================

create_file("src/application/evaluation/metrics.py", """\
def average_speed(speeds):
    return sum(speeds) / len(speeds) if speeds else 0
""")

create_file("src/application/evaluation/risk_metrics.py", """\
def compute_risk_avg(risks):
    return sum(risks) / len(risks) if risks else 0
""")

create_file("src/application/evaluation/evaluator.py", "# evaluation logic\n")

# ==============================
# Monitoring
# ==============================

create_file("src/application/monitoring/logger.py", """\
import csv

def log(data):
    with open("outputs/logs/log.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerow(data)
""")

create_file("src/application/monitoring/dashboard.py", "# optional dashboard\n")

# ==============================
# Utils
# ==============================

create_file("src/utils/build_network.py", "# netconvert script\n")
create_file("src/utils/generate_routes.py", "# randomTrips script\n")

create_file("src/utils/config_loader.py", """\
import yaml

def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)
""")

# ==============================
# Config
# ==============================

create_file("src/config/settings.py", "# global settings\n")

create_file("config/simulation.sumocfg", """\
<configuration>
    <input>
        <net-file value="../network/map.net.xml"/>
        <route-files value="../demand/routes.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
""")

# ==============================
# Experiments
# ==============================

create_file("experiments/base.yaml", """\
name: base
vehicle_rate: 1
""")

create_file("experiments/peak_hour.yaml", """\
name: peak
vehicle_rate: 2
""")

create_file("experiments/incident.yaml", """\
name: incident
vehicle_rate: 3
incident: true
""")

# ==============================
# Misc
# ==============================

create_file("requirements.txt", """\
traci
sumolib
numpy
pandas
matplotlib
pyyaml
""")

create_file("README.md", "# Traffic Digital Twin Project\n")

print("🔥 Project created successfully!")