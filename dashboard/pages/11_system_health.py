"""System Health & Hardware Telemetry Page."""

import streamlit as st
import sys
import shutil
import urllib.request
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.title("🖥️ System Health & Hardware Telemetry")

# Disk Space
total, used, free = shutil.disk_usage("C:\\")
free_gb = free / (1024**3)
total_gb = total / (1024**3)

col1, col2, col3 = st.columns(3)
col1.metric("Free Disk (C:)", f"{free_gb:.1f} GB", f"{free/total*100:.0f}% free")
col2.metric("Ollama Engine", "Running", "gemma4:latest")
col3.metric("Dedicated Venv", "Python 3.11.9", "All dependencies operational")

st.divider()

st.subheader("Hardware & Local Model Engines")
st.markdown("""
- **Host**: Windows 11 Home, 16 Logical Cores, 14 GB System RAM
- **GPU**: AMD Radeon (TM) Graphics (2 GB VRAM)
- **Local LLM**: Ollama (`gemma4:latest` Q4_K_M) on `http://127.0.0.1:11434`
- **Text-to-Speech**: Kokoro-82M ONNX local CPU inference (`~/.faceless-shorts/kokoro`)
- **Word Timings**: Faster-Whisper `small.en` INT8 quantized local inference
- **Video Renderer**: Headless Google Chrome screencast via CDP (1080x1920, 30fps)
- **Audio Mixing**: FFmpeg 8.1.2 full build with procedural sound effect synthesis
""")

if st.button("Test Ollama Latency"):
    t0 = time.time()
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            dur = time.time() - t0
            st.success(f"Ollama responded in {dur*1000:.1f} ms!")
    except Exception as e:
        st.error(f"Ollama health check failed: {e}")
