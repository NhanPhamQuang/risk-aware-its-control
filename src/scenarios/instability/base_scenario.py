"""
Base class for instability risk scenarios.
Reuses existing Digital Twin modules (SumoEnv, StateSync, RiskManager, etc.)

Key difference from congestion base:
  The existing instability_risk(speed) computes np.std([single_value]) which is
  always 0. This base computes PROPER instability via per-vehicle speed CV:

    Ri = std(vehicle_speeds) / mean(vehicle_speeds)

  using traci.lane.getLastStepVehicleIDs() + traci.vehicle.getSpeed()
  to get individual vehicle speeds on each lane.
"""

import os
import csv
import traci
import numpy as np
from datetime import datetime

from src.physical.sumo_env import SumoEnv
from src.twin.state_model import TrafficState
from src.twin.state_sync import StateSync
from src.application.risk.risk_manager import RiskManager
from src.scenarios.logger import ScenarioLogger
from src.application.database.services import ScenarioRunService, MetricsService


class InstabilityBaseScenario:
    """Base class for all instability risk scenarios."""

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
        """Override in subclass to inject instability-causing events."""
        pass

    def run(self):
        """Main simulation loop."""
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

                # Compute proper per-vehicle instability
                instability = self._compute_instability()

                # Collect metrics
                vehicle_count = traci.vehicle.getIDCount()
                record = self._collect_metrics(step, vehicle_count, risks, instability)
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

    def _compute_instability(self):
        """
        Compute proper instability risk per lane:
          Ri = std(vehicle_speeds) / mean(vehicle_speeds)

        This is the Coefficient of Variation (CV) of speed across
        all vehicles on a lane. High CV = vehicles moving at very
        different speeds = unstable flow.
        """
        instability = {}

        for lane in self.state.speed:
            try:
                veh_ids = traci.lane.getLastStepVehicleIDs(lane)

                if len(veh_ids) < 2:
                    instability[lane] = 0.0
                    continue

                speeds = [traci.vehicle.getSpeed(v) for v in veh_ids]
                mean_speed = np.mean(speeds)

                if mean_speed < 0.1:
                    # All vehicles nearly stopped - not instability, just congestion
                    instability[lane] = 0.0
                else:
                    instability[lane] = float(np.std(speeds) / mean_speed)

            except traci.exceptions.TraCIException:
                instability[lane] = 0.0

        return instability

    def _collect_metrics(self, step, vehicle_count, risks, instability):
        """Collect per-step instability metrics."""
        if len(instability) == 0:
            return {
                "step": step,
                "vehicle_count": vehicle_count,
                "avg_instability": 0,
                "max_instability": 0,
                "avg_congestion": 0,
                "max_congestion": 0,
                "unstable_lanes": 0,
                "total_lanes": 0,
                "worst_lane": "",
                "worst_lane_cv": 0,
            }

        ri_values = list(instability.values())
        avg_ri = sum(ri_values) / len(ri_values)
        max_ri = max(ri_values)

        # Lanes with CV > 0.3 are considered unstable
        unstable = sum(1 for v in ri_values if v > 0.3)
        worst_lane = max(instability, key=instability.get)

        # Also track congestion from RiskManager
        avg_c = 0
        max_c = 0
        if risks:
            congestions = [r["congestion"] for r in risks.values()]
            avg_c = sum(congestions) / len(congestions)
            max_c = max(congestions)

        return {
            "step": step,
            "vehicle_count": vehicle_count,
            "avg_instability": round(avg_ri, 4),
            "max_instability": round(max_ri, 4),
            "avg_congestion": round(avg_c, 4),
            "max_congestion": round(max_c, 4),
            "unstable_lanes": unstable,
            "total_lanes": len(instability),
            "worst_lane": worst_lane,
            "worst_lane_cv": round(instability.get(worst_lane, 0), 4),
        }

    def _print_status(self, step, record):
        print(
            f"[Step {step:4d}] vehicles={record['vehicle_count']:3d} | "
            f"avg_Ri={record['avg_instability']:.3f} | "
            f"max_Ri={record['max_instability']:.3f} | "
            f"unstable={record['unstable_lanes']}/{record['total_lanes']}"
        )

    def _get_output_basepath(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        out_dir = os.path.join(project_root, "outputs", "scenarios")
        os.makedirs(out_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(out_dir, f"{self.get_name()}_{timestamp}")

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

    def _export_log(self):
        if hasattr(self, '_output_basepath'):
            self._logger.export(self._output_basepath + ".log")

    def _save_to_db(self, success: bool = True):
        """Persist scenario run metadata and metrics to Postgres."""
        try:
            self._run_id = self._run_svc.start_run("instability", self.get_name())
            self._metrics_svc.insert_rows(self._run_id, "instability", self.log_data)
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

        ri_avg = [r["avg_instability"] for r in self.log_data]
        ri_max = [r["max_instability"] for r in self.log_data]
        vehicles = [r["vehicle_count"] for r in self.log_data]

        peak_step = max(range(len(ri_max)), key=lambda i: ri_max[i])

        print(f"\n{'='*60}")
        print(f"  SUMMARY: {self.get_name()}")
        print(f"{'='*60}")
        print(f"  Total steps:          {len(self.log_data)}")
        print(f"  Peak vehicles:        {max(vehicles)}")
        print(f"  Avg instability (Ri): {sum(ri_avg)/len(ri_avg):.4f}")
        print(f"  Peak avg Ri:          {max(ri_avg):.4f}")
        print(f"  Peak max Ri:          {max(ri_max):.4f} (step {peak_step})")
        print(f"  Steps with max Ri > 0.3:  {sum(1 for r in ri_max if r > 0.3)}")
        print(f"  Steps with max Ri > 0.6:  {sum(1 for r in ri_max if r > 0.6)}")
        print(f"{'='*60}")
