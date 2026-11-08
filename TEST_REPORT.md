# Faceless Shorts Factory: Baseline Inspection and Test Report (Milestone 0)

Date: 2026-11-08  
Host: Windows 11 Home (Build 10.0.26300)  
Architecture: x86_64, 16 logical cores  
RAM: 13.86 GB (4.6 GB available)  
Free Storage (C:): 184.88 GB  
GPU: AMD Radeon(TM) Graphics (2048 MB VRAM)

---

## 1. Environment & Core Tooling Verification

| Component | Path / Location | Version / Status | Verified Capabilities |
|---|---|---|---|
| **Node.js** | `C:\Program Files\nodejs\node.exe` | v26.3.0 | npm, ESM module support (`.mjs`), Playwright / Puppeteer headless execution |
| **FFmpeg** | `C:\ProgramData\chocolatey\bin\ffmpeg.exe` | 8.1.2-full_build | Full audio mixing (`amix`, `dynaudnorm`, `alimiter`), video encoding (`libx264`, `aac`) |
| **Python** | `C:\Program Files\Python311\python.exe` | 3.11.9 | Base Python 64-bit |
| **Dedicated Venv** | `C:\Users\ud127\.faceless-shorts\venv` | Python 3.11.9 | Isolated venv containing ONNX Runtime, Kokoro-ONNX, Faster-Whisper, PyYAML, Requests |
| **Chrome Headless**| `C:\Program Files\Google\Chrome\Application\chrome.exe` | Stable 64-bit | Headless screencast & WebGL canvas frame capture via CDP (Chrome DevTools Protocol) |
| **Git Bash** | `C:\Program Files\Git\bin\bash.exe` | 2.53.0.windows.1 | Posix shell wrapper for automated pipeline execution scripts |
| **Ollama Local LLM**| `http://127.0.0.1:11434` | Running daemon | Model `gemma4:latest` (8.0B parameters, Q4_K_M). Verified 1.4s local inference latency |

---

## 2. Local AI Model Verification

### A. Kokoro-82M ONNX Text-to-Speech
- **Model Path**: `C:\Users\ud127\.faceless-shorts\kokoro\kokoro-v1.0.onnx` (326 MB)
- **Voice Weights**: `C:\Users\ud127\.faceless-shorts\kokoro\voices-v1.0.bin` (27 MB)
- **Primary Voice Verified**: `am_michael` (American Male - deep, clear, authoritative)
- **Alternative Voices**: `af_heart` (American Female), `af_sky`, `am_adam`, `bm_george`, `bf_emma`
- **Output**: 24,000 Hz, 16-bit mono WAV. Generation speed: ~10x realtime on local CPU.

### B. Faster-Whisper Word-Level Alignment
- **Model Name**: `small.en` (INT8 quantized)
- **Model Cache**: HuggingFace local hub (`~/.cache/huggingface/hub/models--Systran--faster-whisper-small.en`)
- **Performance**: Transcribes 35s audio in 1.8s with exact millisecond start/end timestamps per word.

### C. Ollama Gemma4 Local LLM
- **Endpoint**: `http://127.0.0.1:11434/api/generate`
- **Model**: `gemma4:latest` (8.0B parameters)
- **RAM Footprint**: ~5.1 GB when loaded into system RAM.
- **Test Prompt**: *"Return a 1-sentence viral hook for Barings Bank $1 sale."*
- **Response Time**: 1.42 seconds.
- **Output**: *"Did you know a 233-year-old bank that financed the Napoleonic Wars was sold for literally one dollar?"*

---

## 3. Visual Engine Baseline: Selftest of All 6 Styles

Execution of `scripts/selftest.sh --no-voice` across all 6 core visual styles on Windows 11:

| Style Name | Frame Rate / Canvas | Status | Render Time | Review Sheet Generated | Test MP4 Clip |
|---|---|---|---|---|---|
| **Deep Dive 3D** | 30 fps / Three.js 3D | PASSED | 52 s | `_selftest/deep-dive/review/all.jpg` | `_selftest/deep-dive/renders/selftest.mp4` |
| **Inside Out** | 30 fps / 2D Canvas X-Ray | PASSED | 26 s | `_selftest/inside-out/review/all.jpg` | `_selftest/inside-out/renders/selftest.mp4` |
| **Night File 3D** | 30 fps / Atmospheric 3D | PASSED | 47 s | `_selftest/night-file/review/all.jpg` | `_selftest/night-file/renders/selftest.mp4` |
| **Paper Atlas** | 30 fps / Paper craft 2.5D | PASSED | 27 s | `_selftest/paper-atlas/review/all.jpg` | `_selftest/paper-atlas/renders/selftest.mp4` |
| **Stick Story** | 30 fps / 2D Vector Physics | PASSED | 27 s | `_selftest/stick-story/review/all.jpg` | `_selftest/stick-story/renders/selftest.mp4` |
| **Tall Tale 3D** | 30 fps / Low-poly 3D world | PASSED | 82 s | `_selftest/tall-tale/review/all.jpg` | `_selftest/tall-tale/renders/selftest.mp4` |

**Selftest Result Summary**: `SELFTEST PASSED` (6/6 styles operational).

---

## 4. End-to-End Production Baseline: "The Man Who Bought An Entire Bank For $1"

- **Project Path**: `C:\Users\ud127\faceless-shorts\one-dollar-bank`
- **Visual Style**: Tall Tale 3D
- **Narration Duration**: 34.62 seconds (90 words)
- **Total Rendered Frames**: 1,497 frames @ 30 fps
- **Render Engine Time**: 172.4 seconds (8.7 fps capture rate in headless Chrome)
- **Audio Mix Time**: 1.2 seconds (FFmpeg dynamic range normalization + SFX layering)
- **Final Output**: `renders/one-dollar-bank.mp4`
  - Dimensions: 1080 x 1920 (9:16 vertical)
  - Video Codec: H.264 (High profile, Level 4.2)
  - Audio Codec: AAC-LC 192 kbps 48kHz stereo
  - File Size: 31,452,704 bytes (~30.0 MB)
  - Playback Quality: Clear voice, timed captions, smooth 3D camera pan/zoom, SFX on key transitions.

---

## 5. Identified Platform Constraints & Fixes Applied

1. **Windows Console Encoding**:
   - Issue: Python's `estimate.py` crashed on Windows console with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'` (right arrow `→`).
   - Resolution: Replaced `\u2192` with ASCII `->` and enforced `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` in python launcher scripts.
2. **Vertical 9:16 Field of View (FOV)**:
   - Issue: Standard 40° horizontal FOV in vertical 9:16 has a narrow visible width of ~0.82m at 2m distance. In multi-character scenes, actors placed at `x = ±0.6` were clipped out.
   - Resolution: Keep character coordinates within `x ∈ [-0.35, +0.35]` or back the camera up along the z-axis (`z <= -1.2m`).
3. **Execution Shell**:
   - Issue: Native PowerShell syntax differences for bash-based rendering scripts.
   - Resolution: Orchestrator will directly invoke Node.js and Python via standard subprocess using exact file arguments, bypassing bash shell wrappers for guaranteed Windows native stability.

---

## Conclusion
Milestone 0 is complete. All prerequisites, local AI engines, and rendering systems are validated and operating stably on this machine.
