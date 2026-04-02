import os
import sys
import traci
import xml.etree.ElementTree as ET

if "SUMO_HOME" in os.environ:
    sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
else:
    sumo_home = r"C:\Program Files (x86)\Eclipse\Sumo"
    if os.path.isdir(sumo_home):
        os.environ["SUMO_HOME"] = sumo_home
        sys.path.append(os.path.join(sumo_home, "tools"))

class SumoEnv:
    def __init__(self, config_path, gui=True):
        # Resolve relative to project root (2 levels up from this file)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_path = os.path.join(project_root, config_path)
        self.gui = gui
        self.total_steps = self._read_total_steps()

    def _read_total_steps(self):
        """Read simulation end time from sumocfg as the total number of steps."""
        try:
            tree = ET.parse(self.config_path)
            end = tree.find(".//time/end")
            return int(float(end.get("value")))
        except Exception:
            return 3600

    def start(self, extra_args=None):
        binary_name = "sumo-gui" if self.gui else "sumo"
        print(f"Starting {binary_name}...")
        sumo_binary = os.path.join(os.environ["SUMO_HOME"], "bin", binary_name)
        cmd = [sumo_binary, "-c", self.config_path, "--time-to-teleport", "-1"]
        if self.gui:
            cmd += ["--start", "--quit-on-end"]
        if extra_args:
            cmd += extra_args
        traci.start(cmd, numRetries=20)

    def step(self):
        traci.simulationStep()

    def close(self):
        traci.close()