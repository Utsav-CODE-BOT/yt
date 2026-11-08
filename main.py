"""Main CLI Entrypoint for Autonomous Faceless Shorts Factory.

Provides execution modes for manual triggers, Windows Task Scheduler automation,
and background daemon scheduling.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database
from core.orchestrator import DailyOrchestrator
from core.scheduler import Scheduler
from storage.cleanup_manager import CleanupManager


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous Faceless YouTube Shorts Factory"
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Execute the full autonomous 3-video batch for today",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuous scheduler daemon (triggers daily at configured hour in Asia/Kolkata)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date for batch in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--install-task",
        action="store_true",
        help="Print and register Windows Task Scheduler command for 100% autonomous operation",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Run safe previous-day verified MP4 storage cleanup only",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display summary of recent factory jobs and production metrics",
    )

    args = parser.parse_args()

    orchestrator = DailyOrchestrator(factory_root=ROOT)

    if args.install_task:
        scheduler = Scheduler(target_time_str="09:00", timezone_name="Asia/Kolkata")
        python_exe = Path(r"C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe")
        cmd = scheduler.generate_windows_task_command(python_exe, ROOT)
        print("\n=== Windows Task Scheduler Autonomous Registration ===")
        print("To schedule autonomous daily production at 09:00 Asia/Kolkata, run:")
        print(f"\n{cmd}\n")
        return

    if args.cleanup:
        today_str = args.date or orchestrator.job_queue.get_current_date_str()
        print(f"Executing storage cleanup for dates prior to {today_str}...")
        purged = orchestrator.cleanup_mgr.purge_previous_day_verified_mp4s(today_str)
        print(f"Storage cleanup completed. Purged {len(purged)} verified files.")
        return

    if args.status:
        print("\n=== Autonomous Faceless Shorts Factory Status ===")
        with orchestrator.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT job_id, date, slot_number, niche, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 15")
            rows = cursor.fetchall()
            if not rows:
                print("No jobs registered in database yet.")
            else:
                for r in rows:
                    print(f"[{r['date']}] Slot {r['slot_number']} | {r['job_id']} | Status: {r['status']:<18} | Niche: {r['niche']}")
        print("")
        return

    if args.daemon:
        scheduler = Scheduler(target_time_str="09:00", timezone_name="Asia/Kolkata")
        print("Starting in-process autonomous scheduler daemon (Asia/Kolkata 09:00)...")
        scheduler.run_daemon_loop(lambda: orchestrator.run_daily_batch())
        return

    # Default action: run daily batch
    print("\nStarting Autonomous Faceless Shorts Factory batch execution...")
    result = orchestrator.run_daily_batch(target_date=args.date)
    print("\nBatch run finished!")
    print(f"Date: {result['date']}")
    print(f"Jobs Succeeded: {result['jobs_succeeded']} / {result['jobs_executed']}")
    print(f"Report: {result['report_path']}\n")


if __name__ == "__main__":
    main()
