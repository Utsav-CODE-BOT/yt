# Autonomous Faceless YouTube Shorts Factory

Local-First Multi-Niche & Multilingual Daily Content Generation, Quality Control, Publishing, and Storage Management System.

Built on Windows 11 using local and zero-cost AI models with zero paid API dependencies.

---

## 🌟 Key Architecture & Capabilities

1. **Multilingual 12-Shorts/Day Automation**:
   - Generates **12 localized YouTube Shorts every day** (3 daily master topics × 4 Indian languages):
     - 🟡 **Kannada** (`kn-IN` - `kn-IN-GaganNeural`)
     - 🟠 **Hindi** (`hi-IN` - `hi-IN-MadhurNeural`)
     - 🔵 **Telugu** (`te-IN` - `te-IN-MohanNeural`)
     - 🔴 **Tamil** (`ta-IN` - `ta-IN-ValluvarNeural`)
   - **Asset Reuse Optimization**: Visual 3D scene templates, camera trajectories, canvas animations, and shaders are generated **once** per topic and reused across all 4 language variants, minimizing render time, compute, and eliminating duplicate asset costs.

2. **Zero-API Cost Indic TTS & Subtitle Engine**:
   - **Neural TTS**: High-definition Microsoft Neural Edge TTS Indic voices with automatic `gTTS` fallback.
   - **Native Typography**: Complete Indic script support via Windows native `Nirmala UI` (`Nirmala.ttc`) with Unicode Mark category (`\p{M}`) preservation preventing broken glyphs, vowel sign detachment, or virama clipping.
   - **Subtitles & Word Timing**: Millisecond-accurate word-level alignment, responsive font sizing (96–104px), and native text wrapping.

3. **Zero-API Cost Local AI Pipeline**:
   - **LLM**: Local Ollama running `gemma4:latest` (8.0B parameters) for topic ideation, hook generation, scriptwriting, and factual summarization.
   - **Captions & Alignment**: Multi-tier translator (`MyMemory` + `GoogleTranslator`) with conversational tone optimization and line-cut alignment.
   - **Visual Renderer**: Native 6-style HTML5/Canvas/Three.js rendered frame-by-frame via Headless Chrome CDP (1080×1920 @ 30fps) with procedural sound synthesis and FFmpeg audio mixing.

4. **Daily Production Automation**:
   - Produces exactly **three** master topics every day, yielding **12 uploaded shorts**.
   - Enforces diversity across all 3 topics: distinct niches, distinct visual styles, and distinct narrator voices.
   - Runs daily via Windows Task Scheduler or in-process background daemon (`Asia/Kolkata` timezone).

5. **6 Visual Styles Preserved**:
   - `deep-dive`: 3D biological and anatomical explainers (Three.js WebGL).
   - `night-file`: 3D noir atmospheric mystery and investigative explainers.
   - `inside-out`: 2D technical anatomical and cutaway breakdowns.
   - `stick-story`: 2D survival scenarios and practical knowledge.
   - `paper-atlas`: Cut-paper historical map explorations.
   - `tall-tale`: 2D stylized cartoon characters in dynamic 3D environments.

6. **17-State SQLite State Machine & Resumption**:
   - Atomic state transitions stored in `workspace/factory.db`.
   - Idempotent and crash-resilient: if your laptop restarts or loses power mid-render, restarting the pipeline resumes from the last incomplete step without duplicate work or re-uploading.

7. **Automated Quality Control Gate**:
   - **Technical QC**: Validates 1080×1920 resolution, 30fps framerate, valid duration (up to 59.5s), and valid video/audio streams.
   - **Audio QC**: Measures integrated loudness (-14 LUFS target), peak volume, and detects clipping distortion.
   - **Caption QC**: Verifies 100% strictly monotonic timestamp progression, zero overlapping subtitles, and valid Indic word counts.
   - **Visual QC**: Generates and checks contact review sheets for rendered scenes.

8. **YouTube Publishing & Regional Targeting**:
   - Resumable YouTube Data API v3 integration with automated localized title (<60 chars with `#Shorts`), description, citations, and regional tags.
   - Configures YouTube snippet `defaultLanguage` and `defaultAudioLanguage` for optimal regional Shorts recommendation.
   - Built-in verified staging sandbox: if live OAuth credentials are not yet linked, videos stage safely with simulated verification tokens so the pipeline never breaks.

9. **Safe Storage Management**:
   - Automatically purges previous-day verified MP4 exports from `workspace/exports/uploaded/`.
   - Never deletes today's active production videos, project source code, scripts, research records, or SQLite logs.

10. **Streamlit Control Center Dashboard**:
    - 12 interactive dashboard pages for live monitoring, queue management, manual overrides, script inspection, and analytics.

---

## 🚀 Quick Start Guide

### 1. Run Today's 3-Video Batch Manually
```powershell
& "C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe" "C:\Users\ud127\faceless-shorts-factory\main.py" --daily
```

### 2. Check System & Queue Status
```powershell
& "C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe" "C:\Users\ud127\faceless-shorts-factory\main.py" --status
```

### 3. Launch the Streamlit Web Dashboard
```powershell
& "C:\Users\ud127\.faceless-shorts\venv\Scripts\streamlit.exe" run "C:\Users\ud127\faceless-shorts-factory\dashboard\app.py"
```
Then open `http://localhost:8501` in your browser.

### 4. Install Autonomous Windows Task Scheduler
To have Windows automatically execute the factory every morning at 09:00 AM (IST), run in an Administrator PowerShell prompt:
```powershell
schtasks /create /tn "FacelessShortsDailyFactory" /tr "\"C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe\" \"C:\Users\ud127\faceless-shorts-factory\main.py\" --daily" /sc daily /st 09:00 /f /rl HIGHEST
```

### 5. Run as In-Process Daemon
If you prefer running a continuous background loop:
```powershell
& "C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe" "C:\Users\ud127\faceless-shorts-factory\main.py" --daemon
```

---

## 📁 Project Structure

```
faceless-shorts-factory/
├── core/                   # Orchestrator, pipeline, SQLite state machine, queue & logging
│   ├── database.py         # SQLite schema (10 tables)
│   ├── state_machine.py    # 17 persistent states with idempotent resumption
│   ├── job_queue.py        # 3-slot daily queue manager
│   ├── pipeline.py         # Single-job end-to-end pipeline runner
│   ├── orchestrator.py     # Batch daily production runner & audit compiler
│   ├── retry_manager.py    # Exponential backoff retry handler
│   ├── event_logger.py     # SQLite and file event logging
│   └── scheduler.py        # Schedule manager and schtasks generator
├── intelligence/           # Trend discovery, topic scoring, deduplication & niche rotation
│   ├── niche_manager.py    # 10 configured niches & pillar rotation
│   ├── trend_discovery.py  # Wikimedia API & curated evergreen topic adapters
│   ├── topic_scorer.py     # Virality, curiosity, and brevity scoring
│   └── topic_deduplicator.py # Keyword and 3-gram deduplication
├── research/               # Claim extraction, source verification & research logs
│   ├── claim_extractor.py  # Regex/LLM factual claim extraction
│   ├── source_collector.py # Domain credibility ranking
│   ├── fact_verifier.py    # Corroboration confidence evaluation
│   └── research_report.py  # Generates workspace/research/{job_id}_research.md
├── content/                # Local LLM scriptwriting, hooks, translation & validation
│   ├── llm_client.py       # Ollama Gemma4 REST client
│   ├── hook_generator.py   # Generates and ranks 5 distinct opening hooks
│   ├── scriptwriter.py     # Spoken script drafting (45-65 words)
│   ├── script_validator.py # Flesch-Kincaid ease, word count & duration checks
│   ├── translator.py       # Indic translation (Kannada, Hindi, Telugu, Tamil) & metadata
│   ├── retention_analyzer.py # Narrative progression and dropoff prediction
│   └── originality_checker.py # SQLite n-gram similarity checker
├── production/             # Video assembly, TTS, subtitle alignment & rendering
│   ├── style_selector.py   # Distinct style & voice allocator
│   ├── shot_planner.py     # Line cuts and scene transitions
│   ├── project_builder.py  # Master 3D scene builder, font patching & variant generator
│   ├── multilingual_tts.py # Neural Edge TTS Indic voice synthesis & word timing
│   └── renderer.py         # Headless Chrome canvas capture & FFmpeg mix
├── quality/                # Multi-stage automated Quality Control gate
│   ├── technical_checks.py # 1080x1920, 30fps, up to 59.5s duration
│   ├── audio_checks.py     # Integrated LUFS (-14), volume peak clipping
│   ├── caption_checks.py   # Indic Unicode ligatures & monotonic timestamp validation
│   ├── visual_review.py    # Contact sheet verification
│   └── quality_score.py    # 0-100 composite scoring
├── publishing/             # YouTube upload, metadata & affirmative verification
│   ├── metadata_generator.py # Shorts title (<60 chars), description, citations
│   ├── youtube_auth.py     # OAuth token management
│   ├── youtube_upload.py   # Resumable upload with regional language snippet tags
│   └── upload_verifier.py  # Cryptographic upload confirmation token
├── storage/                # Safe disk cleanup
│   └── cleanup_manager.py  # Purges previous-day verified MP4s safely
├── dashboard/              # Streamlit Web Control Center
│   ├── app.py              # Main dashboard launcher
│   └── pages/              # 12 interactive management pages
├── generated/              # Scalable organized multilingual deliverables
│   └── <topic_id>/         # Organized topic bundle
│       ├── kannada/        # Script, audio, subtitle, MP4 & metadata
│       ├── hindi/          # Script, audio, subtitle, MP4 & metadata
│       ├── telugu/         # Script, audio, subtitle, MP4 & metadata
│       └── tamil/          # Script, audio, subtitle, MP4 & metadata
├── workspace/              # Operational storage (DB, exports, logs, research)
│   ├── factory.db          # Master SQLite database
│   ├── exports/pending/    # Daily rendered MP4 exports
│   ├── exports/uploaded/   # Verified uploaded MP4 exports
│   └── logs/factory.log    # Persistent runtime logs
├── reports/                # Daily markdown audit reports (YYYY-MM-DD-daily-report.md)
└── main.py                 # CLI interface
```

---

## 🔒 YouTube OAuth Setup (Optional for Live Production)

To switch from the verified staging sandbox to live publishing on your YouTube channel:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create an OAuth 2.0 Client ID for a Desktop Application.
3. Download the JSON credentials file and save it as:
   `C:\Users\ud127\faceless-shorts-factory\credentials\client_secret.json`
4. The factory will automatically trigger authorization and persist your token in `credentials\token.json`.
