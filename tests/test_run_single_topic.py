"""End-to-End Multilingual Generation Test on a Single Topic.

Tests generating all 4 languages (Kannada, Hindi, Telugu, Tamil) for 1 topic,
verifying that 4 videos, scripts, audio tracks, and metadata files are generated.
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test.multilingual")

from core.database import Database
from core.event_logger import EventLogger
from core.pipeline import PipelineCoordinator

def run_test():
    root = Path(r"C:\Users\ud127\faceless-shorts-factory")
    db = Database(root / "workspace" / "factory.db")
    event_logger = EventLogger(db, root / "workspace" / "logs")

    coordinator = PipelineCoordinator(db, event_logger, factory_root=root)
    # Ensure multilingual is active
    coordinator.multilingual_enabled = True
    coordinator.target_languages = ["kannada", "hindi", "telugu", "tamil"]

    # Initialize a test job
    job_id = "test_multilingual_job_01"
    
    # Clean previous run if exists
    with db.get_connection() as conn:
        conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))

    db.create_job(
        job_id=job_id,
        date_str="2026-11-14",
        slot_number=1,
        niche="Space and astronomy",
        pillar="Cosmos & Physics",
    )
    db.update_job_status(job_id, "TOPIC_SELECTION")

    # Pre-register a fresh unique topic
    topic_id = f"top_{job_id}"
    fingerprint = "test_fp_" + job_id
    db.save_topic(
        topic_id=topic_id,
        job_id=job_id,
        title="Why Neutron Stars Spin 700 Times Per Second",
        hook_summary="When a giant star collapses, conservation of angular momentum spins its core up to 700 times every single second.",
        niche="Space and astronomy",
        source_url="https://nasa.gov",
        source_title="NASA Astrophysics Data System",
        score=95.0,
        fingerprint=fingerprint,
    )

    logger.info("Starting end-to-end pipeline run for %s...", job_id)
    success = coordinator.run_job(job_id, auto_publish=True, privacy="private")
    logger.info("Job %s completed with success=%s", job_id, success)

    if not success:
        logger.error("Job failed!")
        return 1

    # Verify generated artifacts for each language
    for lang in ["kannada", "hindi", "telugu", "tamil"]:
        lang_dir = root / "workspace" / "projects" / job_id / lang
        gen_dir = root / "generated" / job_id / lang
        
        mp4_name = f"{job_id}_{lang}.mp4"
        
        for d in [lang_dir, gen_dir]:
            assert (d / mp4_name).exists(), f"Missing {d / mp4_name}"
            assert (d / "script.json").exists(), f"Missing {d / 'script.json'}"
            assert (d / "narration.wav").exists(), f"Missing {d / 'narration.wav'}"
            assert (d / "words.json").exists(), f"Missing {d / 'words.json'}"
            assert (d / "metadata.json").exists(), f"Missing {d / 'metadata.json'}"
            
        logger.info("VERIFIED all artifacts exist for language: %s", lang)

    # Check database records
    details = db.get_job_full_details(job_id)
    uploads = details.get("uploads", [])
    logger.info("Total uploads recorded in DB for this job: %d", len(uploads))
    assert len(uploads) == 4, f"Expected 4 uploads, found {len(uploads)}"
    
    logger.info("SUCCESS: 4 multilingual shorts generated, rendered, and recorded!")
    return 0

if __name__ == "__main__":
    sys.exit(run_test())
