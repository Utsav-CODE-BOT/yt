"""Database module for Autonomous Faceless Shorts Factory.

Provides SQLite schema initialization, transactional operations, job tracking,
history audit logging, and restart recovery queries.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("factory.database")


def get_current_iso_timestamp() -> str:
    """Return ISO 8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Thread-safe SQLite database manager for factory state."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def get_connection(self):
        """Yield a configured SQLite connection with row factory enabled."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Database transaction rolled back due to error: %s", e)
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables, indexes, and triggers if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Jobs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                slot_number INTEGER NOT NULL,
                niche TEXT NOT NULL,
                pillar TEXT NOT NULL,
                status TEXT NOT NULL,
                current_step TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            )
            """)

            # 2. Topics Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                topic_id TEXT PRIMARY KEY,
                job_id TEXT,
                title TEXT NOT NULL,
                hook_summary TEXT,
                niche TEXT NOT NULL,
                source_url TEXT,
                source_title TEXT,
                score REAL DEFAULT 0.0,
                fingerprint TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE SET NULL
            )
            """)

            # 3. Research Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS research (
                research_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                claims_json TEXT,
                sources_json TEXT,
                passed_verification INTEGER DEFAULT 0,
                report_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
            )
            """)

            # 4. Scripts Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                script_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                chosen_hook TEXT NOT NULL,
                hook_variants_json TEXT,
                script_text TEXT NOT NULL,
                estimated_duration REAL DEFAULT 0.0,
                word_count INTEGER DEFAULT 0,
                pacing_wpm REAL DEFAULT 0.0,
                validation_passed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
            )
            """)

            # 5. Production Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS production (
                production_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                style_name TEXT NOT NULL,
                voice_id TEXT NOT NULL,
                project_dir TEXT NOT NULL,
                audio_path TEXT,
                words_json_path TEXT,
                shots_js_path TEXT,
                render_mp4_path TEXT,
                duration_seconds REAL DEFAULT 0.0,
                fps INTEGER DEFAULT 30,
                render_time_seconds REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )
            """)

            # 6. Quality Checks Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_checks (
                qc_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                overall_score REAL DEFAULT 0.0,
                passed INTEGER DEFAULT 0,
                resolution_check INTEGER DEFAULT 0,
                duration_check INTEGER DEFAULT 0,
                audio_levels_check INTEGER DEFAULT 0,
                caption_sync_check INTEGER DEFAULT 0,
                silence_gap_check INTEGER DEFAULT 0,
                qc_report_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )
            """)

            # 7. Uploads Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                upload_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                video_id TEXT,
                channel_id TEXT,
                youtube_title TEXT NOT NULL,
                youtube_description TEXT,
                youtube_tags_json TEXT,
                privacy_status TEXT DEFAULT 'private',
                upload_url TEXT,
                upload_status TEXT NOT NULL,
                uploaded_at TEXT,
                verified_at TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )
            """)

            # 8. Deletions Table (Safe MP4 Cleanup tracking)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS deletions (
                deletion_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER DEFAULT 0,
                deleted_at TEXT NOT NULL,
                verification_token TEXT NOT NULL,
                backup_archived INTEGER DEFAULT 0,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )
            """)

            # 9. Events Table (Audit Log)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                stage TEXT NOT NULL,
                message TEXT NOT NULL,
                details_json TEXT
            )
            """)

            # 10. Performance / Analytics Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                metric_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                average_view_percentage REAL DEFAULT 0.0,
                retention_at_5s REAL DEFAULT 0.0,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            )
            """)

            # Indexes for fast lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_date ON jobs(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_topics_fingerprint ON topics(fingerprint)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_video_id ON uploads(video_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_job_id ON events(job_id)")

    # -------------------------------------------------------------
    # Job CRUD and State Management
    # -------------------------------------------------------------
    def create_job(
        self,
        job_id: str,
        date_str: str,
        slot_number: int,
        niche: str,
        pillar: str,
        initial_status: str = "IDLE",
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Insert a new job row."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, date, slot_number, niche, pillar, status, current_step, retry_count, max_retries, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (job_id, date_str, slot_number, niche, pillar, initial_status, initial_status, max_retries, now, now),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job record by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_job_status(
        self,
        job_id: str,
        status: str,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update job status and timestamp."""
        now = get_current_iso_timestamp()
        step = current_step or status
        completed_at = now if status in ("COMPLETED", "FAILED") else None

        with self.get_connection() as conn:
            if completed_at:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, current_step = ?, error_message = ?, updated_at = ?, completed_at = ?
                    WHERE job_id = ?
                    """,
                    (status, step, error_message, now, completed_at, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, current_step = ?, error_message = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (status, step, error_message, now, job_id),
                )

    def increment_job_retry(self, job_id: str, error_message: str) -> int:
        """Increment retry counter and record error message."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET retry_count = retry_count + 1, error_message = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (error_message, now, job_id),
            )
            cursor = conn.cursor()
            cursor.execute("SELECT retry_count FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return row["retry_count"] if row else 0

    def get_incomplete_jobs(self) -> List[Dict[str, Any]]:
        """Return jobs that were running or pending before restart."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM jobs
                WHERE status NOT IN ('COMPLETED', 'FAILED', 'CLEANUP')
                ORDER BY created_at ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_jobs_for_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Return all jobs for a specific calendar date."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE date = ? ORDER BY slot_number ASC",
                (date_str,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------
    # Event Logging
    # -------------------------------------------------------------
    def log_event(
        self,
        job_id: Optional[str],
        level: str,
        stage: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an event to the events table."""
        now = get_current_iso_timestamp()
        details_json = json.dumps(details) if details else None
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO events (job_id, timestamp, level, stage, message, details_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, now, level.upper(), stage, message, details_json),
            )

    def get_events_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get chronological audit log for a specific job."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM events WHERE job_id = ? ORDER BY event_id ASC",
                (job_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------
    # Topic Deduplication & Tracking
    # -------------------------------------------------------------
    def is_fingerprint_used(self, fingerprint: str) -> bool:
        """Check if topic fingerprint already exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM topics WHERE fingerprint = ?", (fingerprint,))
            return cursor.fetchone() is not None

    def save_topic(
        self,
        topic_id: str,
        job_id: Optional[str],
        title: str,
        hook_summary: str,
        niche: str,
        source_url: str,
        source_title: str,
        score: float,
        fingerprint: str,
    ) -> None:
        """Insert or replace topic candidate."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO topics
                (topic_id, job_id, title, hook_summary, niche, source_url, source_title, score, fingerprint, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (topic_id, job_id, title, hook_summary, niche, source_url, source_title, score, fingerprint, now),
            )

    def get_recent_topics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get topics used in the last N days."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM topics
                WHERE created_at >= datetime('now', ?)
                ORDER BY created_at DESC
                """,
                (f"-{days} days",),
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------
    # Research, Scripts, Production, Quality & Upload CRUD
    # -------------------------------------------------------------
    def save_research(
        self,
        research_id: str,
        job_id: str,
        topic_id: str,
        claims: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        passed: bool,
        report_path: str,
    ) -> None:
        """Record research claims and fact-check result."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO research
                (research_id, job_id, topic_id, claims_json, sources_json, passed_verification, report_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (research_id, job_id, topic_id, json.dumps(claims), json.dumps(sources), 1 if passed else 0, report_path, now),
            )

    def save_script(
        self,
        script_id: str,
        job_id: str,
        topic_id: str,
        chosen_hook: str,
        hook_variants: List[str],
        script_text: str,
        estimated_duration: float,
        word_count: int,
        pacing_wpm: float,
        validation_passed: bool,
    ) -> None:
        """Record generated script and metrics."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scripts
                (script_id, job_id, topic_id, chosen_hook, hook_variants_json, script_text, estimated_duration, word_count, pacing_wpm, validation_passed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (script_id, job_id, topic_id, chosen_hook, json.dumps(hook_variants), script_text, estimated_duration, word_count, pacing_wpm, 1 if validation_passed else 0, now),
            )

    def save_production(
        self,
        production_id: str,
        job_id: str,
        style_name: str,
        voice_id: str,
        project_dir: str,
        audio_path: str,
        words_json_path: str,
        shots_js_path: str,
        render_mp4_path: str,
        duration_seconds: float,
        fps: int = 30,
        render_time_seconds: float = 0.0,
    ) -> None:
        """Record production assets and rendered paths."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO production
                (production_id, job_id, style_name, voice_id, project_dir, audio_path, words_json_path, shots_js_path, render_mp4_path, duration_seconds, fps, render_time_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (production_id, job_id, style_name, voice_id, project_dir, audio_path, words_json_path, shots_js_path, render_mp4_path, duration_seconds, fps, render_time_seconds, now),
            )

    def save_quality_check(
        self,
        qc_id: str,
        job_id: str,
        overall_score: float,
        passed: bool,
        resolution_check: bool,
        duration_check: bool,
        audio_levels_check: bool,
        caption_sync_check: bool,
        silence_gap_check: bool,
        qc_report: Dict[str, Any],
    ) -> None:
        """Record quality control gate results."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO quality_checks
                (qc_id, job_id, overall_score, passed, resolution_check, duration_check, audio_levels_check, caption_sync_check, silence_gap_check, qc_report_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    qc_id,
                    job_id,
                    overall_score,
                    1 if passed else 0,
                    1 if resolution_check else 0,
                    1 if duration_check else 0,
                    1 if audio_levels_check else 0,
                    1 if caption_sync_check else 0,
                    1 if silence_gap_check else 0,
                    json.dumps(qc_report),
                    now,
                ),
            )

    def save_upload(
        self,
        upload_id: str,
        job_id: str,
        video_id: Optional[str],
        channel_id: Optional[str],
        youtube_title: str,
        youtube_description: str,
        tags: List[str],
        privacy_status: str,
        upload_url: Optional[str],
        upload_status: str,
        uploaded_at: Optional[str] = None,
        verified_at: Optional[str] = None,
    ) -> None:
        """Record or update YouTube upload status."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO uploads
                (upload_id, job_id, video_id, channel_id, youtube_title, youtube_description, youtube_tags_json, privacy_status, upload_url, upload_status, uploaded_at, verified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (upload_id, job_id, video_id, channel_id, youtube_title, youtube_description, json.dumps(tags), privacy_status, upload_url, upload_status, uploaded_at, verified_at),
            )

    def record_deletion(
        self,
        deletion_id: str,
        job_id: str,
        file_path: str,
        file_size_bytes: int,
        verification_token: str,
        backup_archived: bool = True,
    ) -> None:
        """Record verified safe file deletion in manifest."""
        now = get_current_iso_timestamp()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO deletions
                (deletion_id, job_id, file_path, file_size_bytes, deleted_at, verification_token, backup_archived)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (deletion_id, job_id, file_path, file_size_bytes, now, verification_token, 1 if backup_archived else 0),
            )

    def get_job_full_details(self, job_id: str) -> Dict[str, Any]:
        """Aggregate all relational details for a job into a single dictionary."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            job = self.get_job(job_id)
            if not job:
                return {}

            cursor.execute("SELECT * FROM topics WHERE job_id = ?", (job_id,))
            topics = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM research WHERE job_id = ?", (job_id,))
            research = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM scripts WHERE job_id = ?", (job_id,))
            scripts = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM production WHERE job_id = ?", (job_id,))
            production = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM quality_checks WHERE job_id = ?", (job_id,))
            qc = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM uploads WHERE job_id = ?", (job_id,))
            uploads = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM deletions WHERE job_id = ?", (job_id,))
            deletions = [dict(r) for r in cursor.fetchall()]

            return {
                "job": job,
                "topics": topics,
                "research": research,
                "scripts": scripts,
                "production": production,
                "quality_checks": qc,
                "uploads": uploads,
                "deletions": deletions,
            }
