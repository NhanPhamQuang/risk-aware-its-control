"""
Shared logging for all scenario types.
Captures both app console output and SUMO process log into a single .log file
while still printing everything to the console.
"""

import sys
import os
import tempfile
from datetime import datetime


class _TeeWriter:
    """Writes to both the original stdout and a buffer."""

    def __init__(self, original):
        self.original = original
        self.lines = []

    def write(self, text):
        self.original.write(text)
        if text:
            self.lines.append(text)

    def flush(self):
        self.original.flush()


class ScenarioLogger:
    """
    Captures app print() output and SUMO --message-log into a combined .log file.

    Usage:
        logger = ScenarioLogger()
        logger.start()                          # begin capturing stdout
        sumo_args = logger.get_sumo_log_args()  # add to SUMO cmd
        ...                                     # run scenario (all print() captured)
        logger.export(log_filepath)             # write combined .log
        logger.stop()                           # restore stdout
    """

    def __init__(self):
        self._tee = None
        self._original_stdout = None
        self._sumo_log_file = None

    def start(self):
        """Start capturing stdout and create temp file for SUMO log."""
        self._original_stdout = sys.stdout
        self._tee = _TeeWriter(self._original_stdout)
        sys.stdout = self._tee

        # Temp file for SUMO --message-log
        fd, self._sumo_log_file = tempfile.mkstemp(suffix=".sumo.log")
        os.close(fd)

    def get_sumo_log_args(self):
        """Return SUMO CLI args to redirect its log to our temp file."""
        if self._sumo_log_file:
            return ["--message-log", self._sumo_log_file]
        return []

    def export(self, log_filepath):
        """Combine app log + SUMO log into a single .log file with section indicators."""
        # Read SUMO log
        sumo_log = ""
        if self._sumo_log_file and os.path.exists(self._sumo_log_file):
            with open(self._sumo_log_file, "r", errors="replace") as f:
                sumo_log = f.read()

        # Get captured app output
        app_log = "".join(self._tee.lines) if self._tee else ""

        separator = "=" * 70

        with open(log_filepath, "w", encoding="utf-8") as f:
            f.write(f"{separator}\n")
            f.write(f"  [APP LOG] Scenario Console Output\n")
            f.write(f"  Generated: {datetime.now().isoformat()}\n")
            f.write(f"{separator}\n\n")
            f.write(app_log)
            f.write(f"\n\n{separator}\n")
            f.write(f"  [SUMO LOG] SUMO Process Messages\n")
            f.write(f"{separator}\n\n")
            f.write(sumo_log if sumo_log.strip() else "(no SUMO messages)\n")

        # Print log location (goes to console only since we're about to stop)
        print(f"Log exported to: {log_filepath}")

    def get_app_log(self) -> str:
        """Return captured app console output."""
        return "".join(self._tee.lines) if self._tee else ""

    def get_sumo_log(self) -> str:
        """Return captured SUMO process log."""
        if self._sumo_log_file and os.path.exists(self._sumo_log_file):
            with open(self._sumo_log_file, "r", errors="replace") as f:
                return f.read()
        return ""

    def stop(self):
        """Restore original stdout and clean up temp file."""
        if self._original_stdout:
            sys.stdout = self._original_stdout
            self._original_stdout = None
            self._tee = None

        if self._sumo_log_file and os.path.exists(self._sumo_log_file):
            os.remove(self._sumo_log_file)
            self._sumo_log_file = None
