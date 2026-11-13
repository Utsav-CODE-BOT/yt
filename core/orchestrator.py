"""Daily Orchestrator for Autonomous Faceless Shorts Factory.

Coordinates the daily 3-video batch, executes safe previous-day storage cleanup,
recovers interrupted jobs, and compiles the daily production audit report.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import zoneinfo

from core.database import Database
from core.event_logger import EventLogger
from core.job_queue import JobQueue
from core.pipeline import PipelineCoordinator
from intelligence.niche_manager import NicheManager
from storage.cleanup_manager import CleanupManager

logger = logging.getLogger("factory.orchestrator")


class DailyOrchestrator:
    """Master controller for autonomous daily 3-video publishing operations."""

    def __init__(
        self,
        factory_root: str | Path = r"C:\Users\ud127\faceless-shorts-factory",
        timezone_name: str = "Asia/Kolkata",
    ):
        self.root = Path(factory_root)
        self.timezone_name = timezone_name
        self.tz = zoneinfo.ZoneInfo(timezone_name)

        db_path = self.root / "workspace" / "factory.db"
        self.db = Database(db_path)
        self.event_logger = EventLogger(self.db, self.root / "workspace" / "logs")

        self.job_queue = JobQueue(self.db, timezone_name=self.timezone_name)
        self.niche_mgr = NicheManager()
        self.cleanup_mgr = CleanupManager(self.db, self.root / "workspace" / "exports" / "uploaded")
        self.pipeline = PipelineCoordinator(self.db, self.event_logger, factory_root=self.root)

    def run_daily_batch(
        self,
        target_date: Optional[str] = None,
        auto_publish: bool = True,
        privacy: str = "public",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Execute the complete daily autonomous production cycle."""
        today_str = target_date or datetime.now(self.tz).strftime("%Y-%m-%d")
        t_start = time.time()
        logger.info("=================================================================")
        logger.info("STARTING DAILY FACTORY RUN: %s (%s) [Force=%s]", today_str, self.timezone_name, force)
        logger.info("=================================================================")

        # -------------------------------------------------------------
        # STEP 1: Safe Storage Cleanup (Previous Day's Verified MP4s)
        # -------------------------------------------------------------
        logger.info("Phase 1: Executing safe previous-day verified MP4 cleanup...")
        purged_files = self.cleanup_mgr.purge_previous_day_verified_mp4s(
            current_date_str=today_str,
            dry_run=False,
        )

        # -------------------------------------------------------------
        # STEP 2: Niche Selection and Slot Initialization
        # -------------------------------------------------------------
        logger.info("Phase 2: Initializing 3 production slots with distinct niches...")
        day_seed = int(today_str.replace("-", "")) + (99 if force else 0)
        selected_niches = self.niche_mgr.select_daily_niches(day_seed=day_seed)

        slots_config = [
            {"niche": n.name, "pillar": n.pillar}
            for n in selected_niches
        ]

        jobs = self.job_queue.initialize_daily_slots(date_str=today_str, slots=slots_config, force=force)
        logger.info("Production queue ready: %d jobs registered.", len(jobs))

        # -------------------------------------------------------------
        # STEP 3: Sequential Job Execution (Protecting RAM / CPU / GPU)
        # -------------------------------------------------------------
        logger.info("Phase 3: Executing daily production pipeline sequentially...")
        job_results = []
        for job in jobs:
            job_id = job["job_id"]
            slot_num = job["slot_number"]
            niche = job["niche"]

            # Refresh job status from database in case it completed
            curr_job = self.db.get_job(job_id) or job
            if curr_job.get("status") == "COMPLETED":
                logger.info("Slot %d: %s already COMPLETED. Skipping redundant work.", slot_num, job_id)
                job_results.append({
                    "job_id": job_id,
                    "slot": slot_num,
                    "niche": niche,
                    "success": True,
                    "details": self.db.get_job_full_details(job_id),
                })
                continue

            logger.info("--- Starting Production for Slot %d: %s (%s) ---", slot_num, job_id, niche)
            success = self.pipeline.run_job(job_id, auto_publish=auto_publish, privacy=privacy)

            job_detail = self.db.get_job_full_details(job_id)
            job_results.append({
                "job_id": job_id,
                "slot": slot_num,
                "niche": niche,
                "success": success,
                "details": job_detail,
            })

        t_elapsed = time.time() - t_start

        # -------------------------------------------------------------
        # STEP 4: Generate Daily Report
        # -------------------------------------------------------------
        logger.info("Phase 4: Compiling daily audit report...")
        report_path = self._generate_daily_report(today_str, job_results, purged_files, t_elapsed)
        logger.info("Daily report written to %s", report_path)

        logger.info("=================================================================")
        logger.info("DAILY FACTORY RUN COMPLETED IN %.1fs", t_elapsed)
        logger.info("=================================================================")

        return {
            "date": today_str,
            "jobs_executed": len(job_results),
            "jobs_succeeded": sum(1 for j in job_results if j["success"]),
            "purged_previous_day_files": len(purged_files),
            "total_elapsed_seconds": t_elapsed,
            "report_path": str(report_path),
        }

    def _generate_daily_report(
        self,
        date_str: str,
        job_results: List[Dict[str, Any]],
        purged_files: List[Dict[str, Any]],
        elapsed_seconds: float,
    ) -> Path:
        """Write reports/YYYY-MM-DD-daily-report.md."""
        reports_dir = self.root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_file = reports_dir / f"{date_str}-daily-report.md"

        successful_count = sum(1 for j in job_results if j["success"])
        status_banner = "PASSED (3/3 Complete)" if successful_count == 3 else f"PARTIAL ({successful_count}/3 Complete)"

        lines = [
            f"# Daily Content Factory Report: {date_str}",
            "",
            f"- **Execution Date**: {date_str}",
            f"- **Timezone**: {self.timezone_name}",
            f"- **Batch Status**: **{status_banner}**",
            f"- **Total Runtime**: {elapsed_seconds / 60:.1f} minutes",
            f"- **Storage Cleaned**: {len(purged_files)} previous-day MP4 exports safely deleted",
            "",
            "## 1. Daily Multilingual Production Overview (12 Shorts)",
            "",
            "| Slot | Topic ID | Language | Visual Style | Status | Duration | Video URL | QC Score |",
            "|---|---|---|---|---|---|---|---|",
        ]

        total_shorts_count = 0
        for res in job_results:
            details = res["details"]
            job = details.get("job", {})
            prods = details.get("production", [])
            qcs = details.get("quality_checks", [])
            ups = details.get("uploads", [])

            if ups:
                for idx, up in enumerate(ups):
                    total_shorts_count += 1
                    # Match prod and qc for this upload
                    matching_prod = prods[idx] if idx < len(prods) else (prods[0] if prods else {})
                    matching_qc = qcs[idx] if idx < len(qcs) else (qcs[0] if qcs else {})

                    # Extract language from upload_id or voice_id
                    up_id = up.get("upload_id", "")
                    lang = "Default"
                    for candidate_lang in ("kannada", "hindi", "telugu", "tamil"):
                        if candidate_lang in up_id.lower() or candidate_lang in matching_prod.get("voice_id", "").lower():
                            lang = candidate_lang.capitalize()
                            break

                    style = matching_prod.get("style_name", "N/A")
                    status = up.get("upload_status", job.get("status", "UNKNOWN"))
                    dur_val = matching_prod.get("duration_seconds", 0.0)
                    duration = f"{dur_val:.1f}s" if dur_val else "N/A"
                    url = up.get("upload_url", "N/A")
                    qc_val = matching_qc.get("overall_score")
                    qc_score = f"{qc_val:.1f}/100" if qc_val is not None else "N/A"

                    lines.append(
                        f"| {res['slot']} | `{res['job_id']}` | **{lang}** | `{style}` | `{status}` | {duration} | {url} | {qc_score} |"
                    )
            else:
                prod = prods[0] if prods else {}
                qc = qcs[0] if qcs else {}
                style = prod.get("style_name", "N/A")
                status = job.get("status", "UNKNOWN")
                duration = f"{prod.get('duration_seconds', 0.0):.1f}s" if prod else "N/A"
                url = "N/A"
                qc_score = f"{qc.get('overall_score', 0.0):.1f}/100" if qc else "N/A"
                lines.append(
                    f"| {res['slot']} | `{res['job_id']}` | English | `{style}` | `{status}` | {duration} | {url} | {qc_score} |"
                )

        lines.extend([
            "",
            f"**Total Videos Produced & Uploaded**: {total_shorts_count} Shorts",
            "",
            "## 2. Detailed Production Records",
            "",
        ])

        for res in job_results:
            details = res["details"]
            job = details.get("job", {})
            topic = details.get("topics", [{}])[0] if details.get("topics") else {}
            script = details.get("scripts", [{}])[0] if details.get("scripts") else {}
            prod = details.get("production", [{}])[0] if details.get("production") else {}
            up = details.get("uploads", [{}])[0] if details.get("uploads") else {}

            lines.extend([
                f"### Slot {res['slot']}: {topic.get('title', 'Unknown Topic')}",
                f"- **Job ID**: `{res['job_id']}`",
                f"- **Niche**: {res['niche']}",
                f"- **Chosen Hook**: *\"{script.get('chosen_hook', 'N/A')}\"*",
                f"- **Word Count**: {script.get('word_count', 0)} words",
                f"- **Visual Style**: `{prod.get('style_name', 'N/A')}` (Voice: `{prod.get('voice_id', 'N/A')}`)",
                f"- **Render Time**: {prod.get('render_time_seconds', 0.0):.1f}s",
                f"- **Export File**: `{prod.get('render_mp4_path', 'N/A')}`",
                f"- **YouTube Title**: {up.get('youtube_title', 'N/A')}",
                f"- **YouTube Status**: `{up.get('upload_status', 'N/A')}`",
                "",
                "**Full Script Text**:",
                f"> {script.get('script_text', 'N/A')}",
                "",
            ])

        lines.extend([
            "## 3. Storage & Previous-Day Cleanup Manifest",
            "",
            f"The cleanup protocol safely purged {len(purged_files)} verified files from previous daily runs:",
            "",
        ])

        if purged_files:
            lines.append("| Job ID | Deleted File | Date | Size | Status |")
            lines.append("|---|---|---|---|---|")
            for pf in purged_files:
                lines.append(f"| `{pf['job_id']}` | `{pf['file_name']}` | {pf['date']} | {pf['size_bytes'] / (1024*1024):.1f} MB | VERIFIED PURGED |")
        else:
            lines.append("*No previous-day files required pruning on this run.*")

        lines.extend([
            "",
            "---",
            f"*Autonomous Faceless Shorts Factory · Generated on {datetime.now(self.tz).strftime('%Y-%m-%d %H:%M:%S %Z')}*",
            "",
        ])

        report_file.write_text("\n".join(lines), encoding="utf-8")
        return report_file
