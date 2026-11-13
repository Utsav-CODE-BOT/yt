"""Single-Job Pipeline Coordinator for Autonomous Faceless Shorts Factory.

Drives an individual job through the 17 persistent state machine stages with
restart recovery and transactional SQLite updates.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from content.hook_generator import HookGenerator
from content.llm_client import OllamaClient
from content.originality_checker import OriginalityChecker
from content.retention_analyzer import RetentionAnalyzer
from content.script_validator import ScriptValidator
from content.scriptwriter import Scriptwriter
from core.database import Database
from core.event_logger import EventLogger
from core.retry_manager import RetryManager
from core.state_machine import JobStateMachine, PipelineState
from intelligence.topic_deduplicator import TopicDeduplicator
from intelligence.topic_scorer import TopicScorer
from intelligence.trend_discovery import TrendDiscoveryEngine
from production.project_builder import ProjectBuilder
from production.renderer import VideoRenderer
from production.shot_planner import ShotPlanner
from production.style_selector import StyleSelector
from publishing.metadata_generator import MetadataGenerator
from publishing.upload_verifier import UploadVerifier
from publishing.youtube_auth import YouTubeAuth
from publishing.youtube_upload import YouTubeUploader
from quality.quality_score import QualityGate
from research.claim_extractor import ClaimExtractor
from research.fact_verifier import FactVerifier
from research.research_report import ResearchReportGenerator
from research.source_collector import SourceCollector

logger = logging.getLogger("factory.pipeline")


class PipelineCoordinator:
    """Executes a single short-form video job across all architectural phases."""

    def __init__(
        self,
        db: Database,
        event_logger: EventLogger,
        factory_root: str | Path = r"C:\Users\ud127\faceless-shorts-factory",
    ):
        self.db = db
        self.event_logger = event_logger
        self.root = Path(factory_root)

        # Initialize subcomponents
        self.llm = OllamaClient()
        self.retry_mgr = RetryManager(max_retries=3)
        self.dedup = TopicDeduplicator(db)
        self.scorer = TopicScorer(self.dedup)
        self.trend_engine = TrendDiscoveryEngine()

        self.claim_extractor = ClaimExtractor()
        self.source_collector = SourceCollector()
        self.fact_verifier = FactVerifier()
        self.research_report_gen = ResearchReportGenerator(self.root / "workspace" / "research")

        self.hook_gen = HookGenerator(self.llm)
        self.scriptwriter = Scriptwriter(self.llm)
        self.script_validator = ScriptValidator()
        self.retention_analyzer = RetentionAnalyzer()
        self.originality_checker = OriginalityChecker(db)

        self.style_selector = StyleSelector()
        self.shot_planner = ShotPlanner()
        self.project_builder = ProjectBuilder(workspace_root=self.root / "workspace" / "projects")
        self.renderer = VideoRenderer(exports_pending_dir=self.root / "workspace" / "exports" / "pending")
        self.quality_gate = QualityGate()

        self.metadata_gen = MetadataGenerator(self.llm)
        self.auth = YouTubeAuth(credentials_dir=self.root / "credentials")
        self.uploader = YouTubeUploader(
            db,
            self.auth,
            exports_pending_dir=self.root / "workspace" / "exports" / "pending",
            exports_uploaded_dir=self.root / "workspace" / "exports" / "uploaded",
        )
        self.verifier = UploadVerifier(db, self.auth)

    def run_job(self, job_id: str, auto_publish: bool = True, privacy: str = "private") -> bool:
        """Advance job through pipeline stages until completion or failure."""
        job = self.db.get_job(job_id)
        if not job:
            raise ValueError(f"Job ID '{job_id}' not found in database.")

        sm = JobStateMachine(job_id, PipelineState(job["status"]))
        niche = job["niche"]

        def log_stage(stage: str, msg: str, lvl: str = "INFO", details: Optional[Dict[str, Any]] = None):
            self.event_logger.log(job_id, stage, msg, lvl, details)

        full_job = self.db.get_job_full_details(job_id)

        # Handle resumption from FAILED status
        if sm.current_state == PipelineState.FAILED:
            project_dir = self.root / "workspace" / "projects" / job_id
            mp4_render = project_dir / "renders" / f"{job_id}.mp4"

            if full_job.get("uploads") and any(u.get("upload_status") == "VERIFIED" for u in full_job["uploads"]):
                sm.transition_to(PipelineState.COMPLETED, "Resumed: Already verified")
                return True
            elif mp4_render.exists() and mp4_render.stat().st_size > 1_000_000:
                sm.transition_to(PipelineState.VIDEO_RENDERING, "Resumed: Video file exists, resuming at render completion")
            elif full_job.get("scripts"):
                sm.transition_to(PipelineState.SCRIPT_VALIDATION, "Resumed: Script exists, resuming at validation")
            elif full_job.get("topics"):
                sm.transition_to(PipelineState.TOPIC_SELECTION, "Resumed: Topic exists, resuming at research")
            else:
                sm.transition_to(PipelineState.IDLE, "Restarting job")
                sm.transition_to(PipelineState.TOPIC_DISCOVERY, "Discovering candidates")

        try:
            # -------------------------------------------------------------
            # Stage 1: TOPIC_DISCOVERY & TOPIC_SELECTION
            # -------------------------------------------------------------
            if sm.current_state in (PipelineState.IDLE, PipelineState.TOPIC_DISCOVERY):
                sm.transition_to(PipelineState.TOPIC_DISCOVERY, "Discovering candidates")
                self.db.update_job_status(job_id, PipelineState.TOPIC_DISCOVERY.value)
                log_stage("TOPIC_DISCOVERY", f"Gathering topic candidates for niche: {niche}")

                candidates = self.trend_engine.discover_candidates_for_niche(niche, target_count=15)
                ranked = self.scorer.rank_candidates(candidates)
                if not ranked:
                    raise RuntimeError(f"No viable topic candidates found for niche '{niche}'")

                chosen_candidate, candidate_score = ranked[0]

                sm.transition_to(PipelineState.TOPIC_SELECTION, "Candidate selected")
                self.db.update_job_status(job_id, PipelineState.TOPIC_SELECTION.value)
                log_stage(
                    "TOPIC_SELECTION",
                    f"Selected topic: '{chosen_candidate.title}' (Score: {candidate_score:.1f})",
                    details={"title": chosen_candidate.title, "score": candidate_score},
                )

                fingerprint = TopicDeduplicator.generate_fingerprint(
                    chosen_candidate.title, chosen_candidate.summary
                )
                topic_id = f"top_{job_id}"
                self.db.save_topic(
                    topic_id=topic_id,
                    job_id=job_id,
                    title=chosen_candidate.title,
                    hook_summary=chosen_candidate.summary,
                    niche=niche,
                    source_url=chosen_candidate.source_url,
                    source_title=chosen_candidate.source_title,
                    score=candidate_score,
                    fingerprint=fingerprint,
                )

            # Retrieve active topic
            full_job = self.db.get_job_full_details(job_id)
            topics = full_job.get("topics", [])
            active_topic = topics[0] if topics else None
            if not active_topic:
                raise RuntimeError("No active topic registered for job")

            # -------------------------------------------------------------
            # Stage 2: RESEARCH & FACT VERIFICATION
            # -------------------------------------------------------------
            if sm.current_state in (PipelineState.TOPIC_SELECTION, PipelineState.RESEARCH):
                sm.transition_to(PipelineState.RESEARCH, "Verifying factual claims")
                self.db.update_job_status(job_id, PipelineState.RESEARCH.value)
                log_stage("RESEARCH", f"Extracting claims for '{active_topic['title']}'")

                claims = self.claim_extractor.extract_claims(
                    active_topic["hook_summary"], active_topic["title"]
                )
                source_record = self.source_collector.create_source_record(
                    active_topic["source_url"],
                    active_topic["source_title"],
                    active_topic["hook_summary"],
                )
                verification = self.fact_verifier.verify_claims(claims, [source_record], [active_topic["hook_summary"]])

                report_path = self.research_report_gen.generate_report(
                    job_id, active_topic["title"], niche, [source_record], verification
                )

                self.db.save_research(
                    research_id=f"res_{job_id}",
                    job_id=job_id,
                    topic_id=active_topic["topic_id"],
                    claims=[{"statement": c.statement, "type": c.claim_type} for c in claims],
                    sources=[{"title": source_record.title, "url": source_record.url}],
                    passed=verification.passed,
                    report_path=str(report_path),
                )
                log_stage(
                    "RESEARCH",
                    f"Fact verification { 'PASSED' if verification.passed else 'FLAGGED' } (Confidence: {verification.overall_confidence:.1%})",
                    details={"report_path": str(report_path)},
                )

            # -------------------------------------------------------------
            # Stage 3: SCRIPT_GENERATION & VALIDATION
            # -------------------------------------------------------------
            if sm.current_state in (PipelineState.RESEARCH, PipelineState.SCRIPT_GENERATION):
                sm.transition_to(PipelineState.SCRIPT_GENERATION, "Drafting hooks and script")
                self.db.update_job_status(job_id, PipelineState.SCRIPT_GENERATION.value)

                # Generate 5 hooks and pick top 1
                hooks = self.hook_gen.generate_hooks(
                    active_topic["title"], active_topic["hook_summary"], [active_topic["hook_summary"]]
                )
                best_hook = hooks[0].text
                log_stage("SCRIPT_GENERATION", f"Selected hook: \"{best_hook}\"")

                script_obj = self.scriptwriter.generate_script(
                    active_topic["title"],
                    active_topic["hook_summary"],
                    niche,
                    [active_topic["hook_summary"]],
                    best_hook,
                )

                sm.transition_to(PipelineState.SCRIPT_VALIDATION, "Validating duration and pacing")
                self.db.update_job_status(job_id, PipelineState.SCRIPT_VALIDATION.value)

                val_res = self.script_validator.validate(script_obj.full_script)
                ret_rep = self.retention_analyzer.analyze(script_obj.full_script)

                self.db.save_script(
                    script_id=f"scr_{job_id}",
                    job_id=job_id,
                    topic_id=active_topic["topic_id"],
                    chosen_hook=best_hook,
                    hook_variants=[h.text for h in hooks],
                    script_text=script_obj.full_script,
                    estimated_duration=script_obj.estimated_duration_seconds,
                    word_count=script_obj.word_count,
                    pacing_wpm=self.scriptwriter.wpm,
                    validation_passed=val_res.passed,
                )
                log_stage(
                    "SCRIPT_VALIDATION",
                    f"Script validation {'PASSED' if val_res.passed else 'ISSUES'} ({val_res.word_count} words, {val_res.estimated_duration:.1f}s)",
                )

            # Retrieve active script
            full_job = self.db.get_job_full_details(job_id)
            active_script = full_job.get("scripts", [])[0]

            # -------------------------------------------------------------
            # Stage 4: PRODUCTION (VOICE, WORDS, SCENE, RENDER)
            # -------------------------------------------------------------
            project_dir = self.root / "workspace" / "projects" / job_id
            if sm.current_state in (
                PipelineState.SCRIPT_VALIDATION,
                PipelineState.VOICE_GENERATION,
                PipelineState.CAPTION_ALIGNMENT,
                PipelineState.SCENE_PLANNING,
                PipelineState.VIDEO_RENDERING,
            ):
                style_sel = self.style_selector.select_style_for_slot(niche, job["slot_number"])
                project_dir = self.root / "workspace" / "projects" / job_id
                narration_wav = project_dir / "data" / "narration.wav"

                if not narration_wav.exists():
                    sm.transition_to(PipelineState.VOICE_GENERATION, "Synthesizing voiceover")
                    self.db.update_job_status(job_id, PipelineState.VOICE_GENERATION.value)
                    log_stage("VOICE_GENERATION", f"Building project with style '{style_sel.style_name}'")

                    # Build project, run Kokoro and Whisper
                    project_dir = self.project_builder.build_project(
                        job_id=job_id,
                        style_name=style_sel.style_name,
                        script_text=active_script["script_text"],
                        hook=active_script["chosen_hook"],
                        voice_id=style_sel.voice_id,
                        title=active_topic["title"],
                        speed=style_sel.speed,
                    )

                if sm.current_state != PipelineState.VIDEO_RENDERING:
                    sm.transition_to(PipelineState.CAPTION_ALIGNMENT, "Alignment complete")
                    sm.transition_to(PipelineState.SCENE_PLANNING, "Setting shot cuts")
                    sm.transition_to(PipelineState.VIDEO_RENDERING, "Rendering Headless Chrome canvas")
                    self.db.update_job_status(job_id, PipelineState.VIDEO_RENDERING.value)

                log_stage("VIDEO_RENDERING", "Capturing 1080x1920 30fps MP4 frames...")

                render_result = self.renderer.render(project_dir, job_id)

                self.db.save_production(
                    production_id=f"prod_{job_id}",
                    job_id=job_id,
                    style_name=style_sel.style_name,
                    voice_id=style_sel.voice_id,
                    project_dir=str(project_dir),
                    audio_path=str(project_dir / "data" / "narration.wav"),
                    words_json_path=str(project_dir / "data" / "words.json"),
                    shots_js_path=str(project_dir / "src" / "shots.js"),
                    render_mp4_path=str(render_result.mp4_path),
                    duration_seconds=render_result.duration_seconds,
                    fps=render_result.fps,
                    render_time_seconds=render_result.render_time_seconds,
                )
                log_stage(
                    "VIDEO_RENDERING",
                    f"Render complete: {render_result.duration_seconds:.1f}s MP4 in {render_result.render_time_seconds:.1f}s",
                )

            # Retrieve active production
            full_job = self.db.get_job_full_details(job_id)
            active_prod = full_job.get("production", [])[0]
            mp4_file = Path(active_prod["render_mp4_path"])
            sheet_file = project_dir / "review" / "all.jpg"

            # -------------------------------------------------------------
            # Stage 5: QUALITY_CONTROL & APPROVAL
            # -------------------------------------------------------------
            if sm.current_state in (PipelineState.VIDEO_RENDERING, PipelineState.QUALITY_CONTROL):
                sm.transition_to(PipelineState.QUALITY_CONTROL, "Auditing technical, audio, captions, and visual QC")
                self.db.update_job_status(job_id, PipelineState.QUALITY_CONTROL.value)

                qc_result = self.quality_gate.evaluate_production(project_dir, mp4_file, sheet_file)

                self.db.save_quality_check(
                    qc_id=f"qc_{job_id}",
                    job_id=job_id,
                    overall_score=qc_result.overall_score,
                    passed=qc_result.passed,
                    resolution_check=qc_result.technical_passed,
                    duration_check=qc_result.technical_passed,
                    audio_levels_check=qc_result.audio_passed,
                    caption_sync_check=qc_result.caption_passed,
                    silence_gap_check=qc_result.audio_passed,
                    qc_report=qc_result.report,
                )

                if not qc_result.passed:
                    raise RuntimeError(f"Quality Gate failed: {qc_result.all_issues}")

                sm.transition_to(PipelineState.APPROVAL, "QC gate passed, ready for upload")
                self.db.update_job_status(job_id, PipelineState.APPROVAL.value)
                log_stage("APPROVAL", f"Quality gate approved with score {qc_result.overall_score:.1f}/100")

            # -------------------------------------------------------------
            # Stage 6: UPLOADING & VERIFICATION
            # -------------------------------------------------------------
            if auto_publish and sm.current_state in (PipelineState.APPROVAL, PipelineState.UPLOADING):
                sm.transition_to(PipelineState.UPLOADING, "Uploading to YouTube")
                self.db.update_job_status(job_id, PipelineState.UPLOADING.value)

                # Generate metadata
                meta = self.metadata_gen.generate_metadata(
                    topic_title=active_topic["title"],
                    niche=niche,
                    script_text=active_script["script_text"],
                    hook=active_script["chosen_hook"],
                    sources=[SourceCollector().create_source_record(active_topic["source_url"], active_topic["source_title"], "")],
                )

                upload_res = self.uploader.upload(job_id, mp4_file, meta, privacy_status=privacy)

                sm.transition_to(PipelineState.UPLOAD_VERIFICATION, "Verifying live stream status")
                self.db.update_job_status(job_id, PipelineState.UPLOAD_VERIFICATION.value)

                receipt = self.verifier.verify_upload(job_id, upload_res.video_id)
                if not receipt.verified:
                    raise RuntimeError(f"Upload verification failed: {receipt.notes}")

                sm.transition_to(PipelineState.CLEANUP, "Upload verified, ready for lifecycle completion")
                sm.transition_to(PipelineState.COMPLETED, "Daily slot production complete")
                self.db.update_job_status(job_id, PipelineState.COMPLETED.value)
                log_stage("COMPLETED", f"Slot {job['slot_number']} complete and verified on YouTube!")

            return True

        except Exception as exc:
            logger.error("Job %s failed at state %s: %s", job_id, sm.current_state.value, exc, exc_info=True)
            self.db.update_job_status(job_id, PipelineState.FAILED.value, error_message=str(exc))
            log_stage("FAILED", f"Job failed: {exc}", lvl="ERROR", details={"error": str(exc)})
            return False
