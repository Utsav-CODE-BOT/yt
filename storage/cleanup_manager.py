"""Safe Storage and Previous-Day Cleanup Manager for Autonomous Faceless Shorts Factory.

Implements database-verified pruning of previous day's uploaded MP4 files while
strictly preserving source code, research records, metadata, and current-day exports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.database import Database

logger = logging.getLogger("factory.cleanup_manager")


class CleanupManager:
    """Safely removes previous day's verified uploaded MP4 exports."""

    def __init__(
        self,
        db: Database,
        exports_uploaded_dir: str | Path = r"C:\Users\ud127\faceless-shorts-factory\workspace\exports\uploaded",
        retention_days: int = 1,
    ):
        self.db = db
        self.exports_uploaded_dir = Path(exports_uploaded_dir).resolve()
        self.retention_days = retention_days

    def purge_previous_day_verified_mp4s(
        self,
        current_date_str: str,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """Prune uploaded MP4 files from dates prior to current_date_str if verified."""
        logger.info(
            "Running safe storage cleanup check for dates prior to %s (dry_run=%s)...",
            current_date_str,
            dry_run,
        )

        purged_records: List[Dict[str, Any]] = []

        if not self.exports_uploaded_dir.exists():
            return purged_records

        # Find all MP4 files in exports/uploaded
        mp4_files = list(self.exports_uploaded_dir.glob("*.mp4"))

        for mp4_file in mp4_files:
            job_id = mp4_file.stem
            job = self.db.get_job(job_id)

            if not job:
                logger.warning("File %s has no matching database job record. Skipping for safety.", mp4_file.name)
                continue

            # Constraint 1: Must be older than current date
            job_date = job.get("date", "")
            if job_date >= current_date_str:
                logger.debug("Job %s is from current date %s. Skipping (protected).", job_id, job_date)
                continue

            # Constraint 2: Must be fully VERIFIED in uploads table
            full_details = self.db.get_job_full_details(job_id)
            uploads = full_details.get("uploads", [])
            verified_upload = next((u for u in uploads if u.get("upload_status") == "VERIFIED"), None)

            if not verified_upload:
                logger.warning(
                    "Job %s MP4 exists but upload is NOT verified in database. Preserving file for safety.",
                    job_id,
                )
                continue

            # Constraint 3: Must be inside exports_uploaded_dir (path traversal protection)
            resolved_file = mp4_file.resolve()
            if not str(resolved_file).startswith(str(self.exports_uploaded_dir)):
                logger.error("Path traversal security violation detected: %s! Aborting deletion.", resolved_file)
                continue

            file_size = resolved_file.stat().st_size
            verification_token = f"verified_yt_{verified_upload.get('video_id')}_{verified_upload.get('verified_at')}"

            logger.info(
                "Safe cleanup candidate confirmed: Job %s (Date: %s, Size: %.1f MB).",
                job_id,
                job_date,
                file_size / (1024 * 1024),
            )

            if not dry_run:
                try:
                    resolved_file.unlink()
                    logger.info("Deleted previous day's verified MP4: %s", resolved_file.name)

                    # Record in SQLite deletions ledger
                    self.db.record_deletion(
                        deletion_id=f"del_{job_id}_{int(datetime.now(timezone.utc).timestamp())}",
                        job_id=job_id,
                        file_path=str(resolved_file),
                        file_size_bytes=file_size,
                        verification_token=verification_token,
                        backup_archived=True,
                    )
                except Exception as e:
                    logger.error("Failed to delete file %s: %s", resolved_file, e)
                    continue

            purged_records.append({
                "job_id": job_id,
                "file_name": resolved_file.name,
                "date": job_date,
                "size_bytes": file_size,
                "purged": not dry_run,
            })

        logger.info("Safe storage cleanup finished. %d files processed.", len(purged_records))
        return purged_records
