"""
Base class for congestion risk scenarios.
Reuses existing Digital Twin modules (SumoEnv, StateSync, RiskManager, etc.)
Each scenario subclass overrides inject_perturbation() to trigger congestion.
"""

import os
import csv
import time
import traci
from datetime import datetime

from src.physical.sumo_env import SumoEnv
from src.twin.state_model import TrafficState
from src.twin.state_sync import StateSync
from src.application.risk.risk_manager import RiskManager
from src.scenarios.logger import ScenarioLogger
from src.application.database.services import ScenarioRunService, MetricsService


class BaseScenario:
    """Base class for all congestion risk scenarios."""

    def __init__(self, total_steps=None, config_path="config/simulation.sumocfg", gui=True):
        self.config_path = config_path

        # Reuse existing modules
        self.env = SumoEnv(config_path, gui=gui)
        self.total_steps = total_steps if total_steps is not None else self.env.total_steps
        self.state = TrafficState()
        self.sync = StateSync()
        self.risk_manager = RiskManager()

        # Logging
        self.log_data = []
        self._logger = ScenarioLogger()

        # Database
        self._run_svc = ScenarioRunService()
        self._run_svc.ensure_table()
        self._metrics_svc = MetricsService(conn=self._run_svc.conn)
        self._metrics_svc.ensure_tables()
        self._run_id = None

    def get_name(self):
        raise NotImplementedError

    def get_description(self):
        raise NotImplementedError

    def inject_perturbation(self, step):
        """Override in subclass to inject congestion-causing events."""
        pass

    def run(self):
        """Main simulation loop - reuses the same architecture as main.py."""
        self._logger.start()

        print(f"\n{'='*60}")
        print(f"  SCENARIO: {self.get_name()}")
        print(f"  {self.get_description()}")
        print(f"  Steps: {self.total_steps}")
        print(f"{'='*60}\n")

        self.env.start(extra_args=self._logger.get_sumo_log_args())
        print("SUMO started")

        try:
            for step in range(self.total_steps):
                self.env.step()

                # Inject scenario-specific perturbation
                self.inject_perturbation(step)

                # Sync physical -> twin (reuse StateSync)
                density, speed, queue = self.sync.sync()
                self.state.update(density, speed, queue)

                # Compute risks (reuse RiskManager)
                risks = self.risk_manager.compute(self.state)

                # Collect metrics
                vehicle_count = traci.vehicle.getIDCount()
                record = self._collect_metrics(step, vehicle_count, risks)
                self.log_data.append(record)

                # Debug output every 50 steps
                if step % 50 == 0:
                    self._print_status(step, record)

        except traci.exceptions.FatalTraCIError:
            print(f"SUMO closed at step {step}")
        finally:
            self.env.close()

        # Export results
        self._export_csv()
        self._print_summary()
        self._save_to_db(success=True)
        self._export_log()
        self._logger.stop()

    def _collect_metrics(self, step, vehicle_count, risks):
        """Collect per-step congestion metrics."""
        if len(risks) == 0:
            return {
                "step": step,
                "vehicle_count": vehicle_count,
                "avg_congestion": 0,
                "max_congestion": 0,
                "avg_spillback": 0,
                "max_spillback": 0,
                "congested_lanes": 0,
                "total_lanes": 0,
                "worst_lane": "",
            }

        congestions = [r["congestion"] for r in risks.values()]
        spillbacks = [r["spillback"] for r in risks.values()]

        avg_c = sum(congestions) / len(congestions)
        max_c = max(congestions)
        avg_s = sum(spillbacks) / len(spillbacks)
        max_s = max(spillbacks)

        # Count lanes above congestion threshold (Rc > 0.6)
        congested = sum(1 for c in congestions if c > 0.6)
        worst_lane = max(risks, key=lambda k: risks[k]["congestion"])

        return {
            "step": step,
            "vehicle_count": vehicle_count,
            "avg_congestion": round(avg_c, 4),
            "max_congestion": round(max_c, 4),
            "avg_spillback": round(avg_s, 4),
            "max_spillback": round(max_s, 4),
            "congested_lanes": congested,
            "total_lanes": len(risks),
            "worst_lane": worst_lane,
        }

    def _print_status(self, step, record):
        print(
            f"[Step {step:4d}] vehicles={record['vehicle_count']:3d} | "
            f"avg_Rc={record['avg_congestion']:.3f} | "
            f"max_Rc={record['max_congestion']:.3f} | "
            f"congested={record['congested_lanes']}/{record['total_lanes']}"
        )

    def _export_csv(self):
        """Export results to CSV in outputs/scenarios/."""
        if not self.log_data:
            return

        self._output_basepath = self._get_output_basepath()
        filepath = self._output_basepath + ".csv"

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.log_data[0].keys())
            writer.writeheader()
            writer.writerows(self.log_data)

        print(f"\nResults exported to: {filepath}")

    def _get_output_basepath(self):
        """Return the base path (without extension) for output files."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        out_dir = os.path.join(project_root, "outputs", "scenarios")
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(out_dir, f"{self.get_name()}_{timestamp}")

    def _export_log(self):
        """Export combined app + SUMO log to .log file alongside .csv."""
        if hasattr(self, '_output_basepath'):
            self._logger.export(self._output_basepath + ".log")

    def _save_to_db(self, success: bool = True):
        """Persist scenario run metadata and metrics to Postgres."""
        try:
            self._run_id = self._run_svc.start_run("congestion", self.get_name())
            self._metrics_svc.insert_rows(self._run_id, "congestion", self.log_data)
            self._run_svc.finish_run(
                self._run_id,
                success=success,
                sumo_log=self._logger.get_sumo_log(),
                app_log=self._logger.get_app_log(),
            )
            print(f"  [DB] Saved run {self._run_id} ({len(self.log_data)} rows)")
        except Exception as e:
            print(f"  [DB] Failed to save: {e}")

    def _print_summary(self):
        """Print summary statistics."""
        if not self.log_data:
            print("No data collected.")
            return

        congestions = [r["avg_congestion"] for r in self.log_data]
        max_congestions = [r["max_congestion"] for r in self.log_data]
        vehicles = [r["vehicle_count"] for r in self.log_data]

        # Find peak congestion window
        peak_step = max(range(len(max_congestions)), key=lambda i: max_congestions[i])

        print(f"\n{'='*60}")
        print(f"  SUMMARY: {self.get_name()}")
        print(f"{'='*60}")
        print(f"  Total steps:          {len(self.log_data)}")
        print(f"  Peak vehicles:        {max(vehicles)}")
        print(f"  Avg congestion (Rc):  {sum(congestions)/len(congestions):.4f}")
        print(f"  Peak avg Rc:          {max(congestions):.4f}")
        print(f"  Peak max Rc:          {max(max_congestions):.4f} (step {peak_step})")
        print(f"  Steps with max Rc > 0.6:  {sum(1 for c in max_congestions if c > 0.6)}")
        print(f"  Steps with max Rc > 1.0:  {sum(1 for c in max_congestions if c > 1.0)}")
        print(f"{'='*60}")
