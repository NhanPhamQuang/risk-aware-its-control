"""
Base class for spillback risk scenarios.
Reuses existing Digital Twin modules (SumoEnv, StateSync, RiskManager, etc.)

Spillback = queues that overflow beyond a lane's storage capacity, blocking
upstream intersections and propagating through the network.

Key metrics tracked:
  - Rs from RiskManager: queue / lane_length (existing)
  - Raw queue counts per lane (halted vehicles)
  - Queue propagation: whether upstream lanes are also queued
  - Total network halted vehicles

Network topology (for spillback analysis):
  Junction 2 is the central hub with 4 approach lanes:
    -100#1_0 (west), -101#1_0 (south), 100#0_0 (east), 101#0_0 (north)
  Exit lanes from J2:
    100#1_0 (east), -100#0_0 (west), 101#1_0 (north), -101#0_0 (south)
"""

import os
import csv
import traci
from datetime import datetime

from src.physical.sumo_env import SumoEnv
from src.twin.state_model import TrafficState
from src.twin.state_sync import StateSync
from src.application.risk.risk_manager import RiskManager
from src.scenarios.logger import ScenarioLogger
from src.application.database.services import ScenarioRunService, MetricsService


# Network topology: approach lanes -> exit lanes at central junction 2
JUNCTION2_APPROACH = ["-100#1_0", "-101#1_0", "100#0_0", "101#0_0"]
JUNCTION2_EXIT = ["100#1_0", "-100#0_0", "101#1_0", "-101#0_0"]


class SpillbackBaseScenario:
    """Base class for all spillback risk scenarios."""

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
        """Override in subclass to inject spillback-causing events."""
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

                # Compute enhanced spillback metrics
                spillback_data = self._compute_spillback()

                # Collect metrics
                vehicle_count = traci.vehicle.getIDCount()
                record = self._collect_metrics(step, vehicle_count, risks, spillback_data)
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

    def _compute_spillback(self):
        """
        Compute enhanced spillback metrics per lane:
          - queue: raw halted vehicle count
          - Rs: from existing spillback_risk (queue / 50)
          - propagation: True if both this lane AND its downstream lane have queues
        """
        data = {}

        for lane in self.state.queue:
            queue = self.state.queue[lane]
            rs = queue / 50  # same as spillback_risk()

            # Check if downstream lanes also have queues (propagation)
            propagating = False
            try:
                links = traci.lane.getLinks(lane)
                for link in links:
                    next_lane = link[0]
                    if next_lane in self.state.queue and self.state.queue[next_lane] > 0:
                        if queue > 0:
                            propagating = True
                            break
            except traci.exceptions.TraCIException:
                pass

            data[lane] = {
                "queue": queue,
                "rs": rs,
                "propagating": propagating,
            }

        return data

    def _collect_metrics(self, step, vehicle_count, risks, spillback_data):
        """Collect per-step spillback metrics."""
        if not spillback_data:
            return {
                "step": step,
                "vehicle_count": vehicle_count,
                "avg_spillback": 0,
                "max_spillback": 0,
                "avg_congestion": 0,
                "total_queue": 0,
                "max_queue": 0,
                "spillback_lanes": 0,
                "propagating_lanes": 0,
                "total_lanes": 0,
                "worst_lane": "",
                "worst_lane_queue": 0,
            }

        rs_values = [d["rs"] for d in spillback_data.values()]
        queues = [d["queue"] for d in spillback_data.values()]

        avg_rs = sum(rs_values) / len(rs_values)
        max_rs = max(rs_values)
        total_queue = sum(queues)
        max_queue = max(queues)

        # Lanes with Rs > 0.1 (at least 5 halted vehicles)
        spillback_lanes = sum(1 for rs in rs_values if rs > 0.1)
        # Lanes where queue is propagating downstream
        propagating = sum(1 for d in spillback_data.values() if d["propagating"])

        worst_lane = max(spillback_data, key=lambda k: spillback_data[k]["queue"])

        # Congestion from RiskManager
        avg_c = 0
        if risks:
            congestions = [r["congestion"] for r in risks.values()]
            avg_c = sum(congestions) / len(congestions)

        return {
            "step": step,
            "vehicle_count": vehicle_count,
            "avg_spillback": round(avg_rs, 4),
            "max_spillback": round(max_rs, 4),
            "avg_congestion": round(avg_c, 4),
            "total_queue": total_queue,
            "max_queue": max_queue,
            "spillback_lanes": spillback_lanes,
            "propagating_lanes": propagating,
            "total_lanes": len(spillback_data),
            "worst_lane": worst_lane,
            "worst_lane_queue": spillback_data[worst_lane]["queue"],
        }

    def _print_status(self, step, record):
        print(
            f"[Step {step:4d}] vehicles={record['vehicle_count']:3d} | "
            f"avg_Rs={record['avg_spillback']:.3f} | "
            f"max_Rs={record['max_spillback']:.3f} | "
            f"queue={record['total_queue']:3d} | "
            f"spill={record['spillback_lanes']}/{record['total_lanes']} | "
            f"propagating={record['propagating_lanes']}"
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
            self._run_id = self._run_svc.start_run("spillback", self.get_name())
            self._metrics_svc.insert_rows(self._run_id, "spillback", self.log_data)
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

        rs_avg = [r["avg_spillback"] for r in self.log_data]
        rs_max = [r["max_spillback"] for r in self.log_data]
        queues = [r["total_queue"] for r in self.log_data]
        vehicles = [r["vehicle_count"] for r in self.log_data]
        propagating = [r["propagating_lanes"] for r in self.log_data]

        peak_step = max(range(len(rs_max)), key=lambda i: rs_max[i])

        print(f"\n{'='*60}")
        print(f"  SUMMARY: {self.get_name()}")
        print(f"{'='*60}")
        print(f"  Total steps:           {len(self.log_data)}")
        print(f"  Peak vehicles:         {max(vehicles)}")
        print(f"  Avg spillback (Rs):    {sum(rs_avg)/len(rs_avg):.4f}")
        print(f"  Peak avg Rs:           {max(rs_avg):.4f}")
        print(f"  Peak max Rs:           {max(rs_max):.4f} (step {peak_step})")
        print(f"  Peak total queue:      {max(queues)}")
        print(f"  Peak propagating:      {max(propagating)} lanes")
        print(f"  Steps with max Rs > 0.1:   {sum(1 for r in rs_max if r > 0.1)}")
        print(f"  Steps with max Rs > 0.5:   {sum(1 for r in rs_max if r > 0.5)}")
        print(f"{'='*60}")
