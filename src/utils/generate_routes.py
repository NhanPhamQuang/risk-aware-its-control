import os
import subprocess

def generate(period=1, duration=3600):
    sumo_home = os.environ.get("SUMO_HOME")

    if not sumo_home:
        raise EnvironmentError("SUMO_HOME not set")

    random_trips = os.path.join(sumo_home, "tools", "randomTrips.py")

    cmd = [
        "python",
        random_trips,
        "-n", "network/map.net.xml",
        "-o", "demand/trips.xml",
        "-r", "demand/routes.rou.xml",
        "--period", str(period),          # 🔥 càng nhỏ càng đông xe
        "--end", str(duration),
        "--validate"
    ]

    print("🚗 Generating traffic with period =", period)
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    generate()