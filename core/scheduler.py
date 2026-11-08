"""Scheduler and Windows Automation Integrator for Autonomous Faceless Shorts Factory.

Supports cron-like local execution in Asia/Kolkata timezone, immediate triggers,
and Windows Task Scheduler registration scripts.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
import zoneinfo

logger = logging.getLogger("factory.scheduler")


class Scheduler:
    """Calculates trigger times, coordinates daily batch execution, and registers OS tasks."""

    def __init__(self, target_time_str: str = "09:00", timezone_name: str = "Asia/Kolkata"):
        self.target_time_str = target_time_str
        self.timezone_name = timezone_name
        self.tz = zoneinfo.ZoneInfo(timezone_name)
        hour, minute = map(int, target_time_str.split(":"))
        self.hour = hour
        self.minute = minute

    def get_next_run_datetime(self) -> datetime:
        """Calculate the next scheduled datetime in target timezone."""
        now = datetime.now(self.tz)
        target = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    def seconds_until_next_run(self) -> float:
        """Return float seconds until the next scheduled trigger."""
        next_dt = self.get_next_run_datetime()
        now = datetime.now(self.tz)
        return max(0.0, (next_dt - now).total_seconds())

    def run_daemon_loop(self, job_runner_callable: Callable[[], None], poll_interval: float = 30.0) -> None:
        """In-process background scheduler loop."""
        logger.info(
            "Starting scheduler loop for %s %s. Next run scheduled for %s.",
            self.target_time_str,
            self.timezone_name,
            self.get_next_run_datetime().isoformat(),
        )

        last_executed_date: Optional[str] = None

        while True:
            now = datetime.now(self.tz)
            today_str = now.strftime("%Y-%m-%d")

            # Check if current time is at or past target hour:minute and not yet run today
            if (now.hour > self.hour or (now.hour == self.hour and now.minute >= self.minute)) and last_executed_date != today_str:
                logger.info("Daily trigger reached for date %s at %s. Executing batch...", today_str, now.isoformat())
                try:
                    job_runner_callable()
                    last_executed_date = today_str
                except Exception as exc:
                    logger.error("Error executing daily scheduled batch: %s", exc, exc_info=True)

            time.sleep(poll_interval)

    def generate_windows_task_command(self, python_exe: Path, factory_dir: Path) -> str:
        """Generate schtasks command to register daily automatic trigger on Windows."""
        task_name = "FacelessShortsDailyFactory"
        py_path = str(python_exe).replace("/", "\\")
        runner_script = str(factory_dir / "main.py").replace("/", "\\")
        cmd = f'"{py_path}" "{runner_script}" --daily'

        # Runs daily at configured time
        schtask = (
            f'schtasks /create /tn "{task_name}" /tr "{cmd}" '
            f'/sc daily /st {self.target_time_str} /f /rl HIGHEST'
        )
        return schtask
