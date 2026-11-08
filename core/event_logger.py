"""Centralized Event Logger for Autonomous Faceless Shorts Factory.

Provides dual-destination structured logging to console, local rotating log files,
and the SQLite events audit trail.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from core.database import Database


class EventLogger:
    """Dispatches logging records to Python standard logger and the SQLite database."""

    def __init__(self, db: Database, log_dir: str | Path):
        self.db = db
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_file_logging()

    def _setup_file_logging(self) -> None:
        """Configure root factory logger with file and console streams."""
        root_logger = logging.getLogger("factory")
        root_logger.setLevel(logging.DEBUG)

        if not root_logger.handlers:
            # File handler
            log_file = self.log_dir / "factory.log"
            fh = logging.FileHandler(str(log_file), encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
            )
            fh.setFormatter(file_formatter)
            root_logger.addHandler(fh)

            # Console handler
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
            )
            ch.setFormatter(console_formatter)
            root_logger.addHandler(ch)

    def log(
        self,
        job_id: Optional[str],
        stage: str,
        message: str,
        level: str = "INFO",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log event to standard logging and write to database."""
        lvl = level.upper()
        logger_instance = logging.getLogger(f"factory.{stage.lower()}")

        log_fn = {
            "DEBUG": logger_instance.debug,
            "INFO": logger_instance.info,
            "WARNING": logger_instance.warning,
            "ERROR": logger_instance.error,
            "CRITICAL": logger_instance.critical,
        }.get(lvl, logger_instance.info)

        prefix = f"[{job_id}] " if job_id else ""
        log_fn("%s%s", prefix, message)

        try:
            self.db.log_event(
                job_id=job_id,
                level=lvl,
                stage=stage,
                message=message,
                details=details,
            )
        except Exception as e:
            logger_instance.error("Failed to write event to SQLite: %s", e)
