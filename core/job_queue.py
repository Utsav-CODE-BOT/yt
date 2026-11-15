"""Job Queue and Daily Production Slot Manager.

Orchestrates the daily 3-video slot requirement, ensures niche variation,
and prevents overlapping execution on resource-constrained local hardware.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import zoneinfo

from core.database import Database

logger = logging.getLogger("factory.job_queue")


class JobQueue:
    """Manages slot allocation and sequencing of daily production jobs."""

    def __init__(self, db: Database, timezone_name: str = "Asia/Kolkata"):
        self.db = db
        self.tz = zoneinfo.ZoneInfo(timezone_name)

    def get_current_date_str(self) -> str:
        """Return YYYY-MM-DD formatted date in configured timezone."""
        return datetime.now(self.tz).strftime("%Y-%m-%d")

    def initialize_daily_slots(
        self,
        date_str: Optional[str] = None,
        slots: Optional[List[Dict[str, str]]] = None,
        force: bool = False,
    ) -> List[Dict[str, Any]]:
        """Ensure exactly 3 distinct slots exist in SQLite for the specified day.

        slots is an optional list of dictionaries with 'niche' and 'pillar'.
        If omitted, defaults are supplied from configuration.
        If force=True, creates a fresh additional batch of 3 slots for today.
        """
        target_date = date_str or self.get_current_date_str()
        expected_prefix = f"job_{target_date.replace('-', '')}"
        all_existing = self.db.get_jobs_for_date(target_date)
        existing_jobs = [j for j in all_existing if j["job_id"].startswith(expected_prefix)]

        if not force and len(existing_jobs) >= 3:
            logger.info("Daily slots for %s already exist (%d production jobs found).", target_date, len(existing_jobs))
            return existing_jobs

        default_slots = [
            {"slot": 1, "niche": "Ancient history and civilizations", "pillar": "Ancient Civilizations & Archaeology"},
            {"slot": 2, "niche": "History and historical mysteries", "pillar": "Lost Civilizations & Enigmas"},
            {"slot": 3, "niche": "Historical turning points and extraordinary events", "pillar": "Turning Points & True Drama"},
        ]

        if slots and len(slots) == 3:
            default_slots = [
                {"slot": i + 1, "niche": s["niche"], "pillar": s.get("pillar", "General")}
                for i, s in enumerate(slots)
            ]

        batch_suffix = f"_b{len(existing_jobs)//3 + 1}" if force else ""
        created_jobs = []
        for slot_info in default_slots:
            slot_num = slot_info["slot"]
            if not force:
                found = next((j for j in existing_jobs if j["slot_number"] == slot_num and j["job_id"].startswith(expected_prefix)), None)
                if found:
                    created_jobs.append(found)
                    continue

            job_id = f"job_{target_date.replace('-', '')}{batch_suffix}_{slot_num:02d}"
            job = self.db.create_job(
                job_id=job_id,
                date_str=target_date,
                slot_number=slot_num + (len(existing_jobs) if force else 0),
                niche=slot_info["niche"],
                pillar=slot_info["pillar"],
                initial_status="IDLE",
            )
            logger.info("Created daily production slot: %s (Slot %d, %s)", job_id, slot_num, slot_info["niche"])
            created_jobs.append(job)

        return created_jobs

    def get_pending_jobs(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return incomplete jobs for the current day or recovered incomplete jobs."""
        target_date = date_str or self.get_current_date_str()
        # Daily slots for target date takes precedence
        daily_jobs = self.initialize_daily_slots(target_date)
        pending_daily = [j for j in daily_jobs if j["status"] not in ("COMPLETED", "FAILED")]
        if pending_daily:
            return pending_daily

        # Otherwise check legitimate production incomplete jobs across system
        incompletes = [j for j in self.db.get_incomplete_jobs() if j["job_id"].startswith("job_")]
        return incompletes
