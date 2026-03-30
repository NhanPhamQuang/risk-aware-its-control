import traci

class SumoEnv:
    def __init__(self, config_path):
        self.config_path = config_path

    def start(self):
        print("Starting SUMO GUI...")
        traci.start([
            "sumo-gui",
            "-c", self.config_path,
            "--start",           # 🔥 auto play
            "--quit-on-end"
        ])

    def step(self):
        traci.simulationStep()

    def close(self):
        traci.close()