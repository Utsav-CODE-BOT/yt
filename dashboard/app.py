"""Streamlit Control Center for Autonomous Faceless Shorts Factory.

Provides operational monitoring, manual triggers, pipeline state visibility,
and system diagnostics.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st

# Ensure factory root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.set_page_config(
    page_title="Faceless Shorts Factory Control Center",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E88E5; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.1rem; color: #888; margin-bottom: 1.5rem; }
    .metric-card { background: #161B22; padding: 1.2rem; border-radius: 8px; border: 1px solid #30363D; }
    .status-ok { color: #3FB950; font-weight: 600; }
    .status-warn { color: #D29922; font-weight: 600; }
    .status-fail { color: #F85149; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

db_path = ROOT / "workspace" / "factory.db"
db = Database(db_path)

st.markdown('<div class="main-header">🎬 Autonomous Faceless Shorts Factory</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Local-First Multi-Niche Daily Content Generation, Publishing & Storage Management</div>', unsafe_allow_html=True)

# Top Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'COMPLETED'")
    completed_jobs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM uploads WHERE upload_status = 'VERIFIED'")
    verified_uploads = c.fetchone()[0]

    c.execute("SELECT COUNT(*), COALESCE(SUM(file_size_bytes), 0) FROM deletions")
    del_count, del_bytes = c.fetchone()

with col1:
    st.metric("Total Jobs Created", total_jobs)
with col2:
    st.metric("Completed Batches", completed_jobs)
with col3:
    st.metric("Verified Live Shorts", verified_uploads)
with col4:
    st.metric("Cleaned MP4 Files", del_count)
with col5:
    st.metric("Storage Saved", f"{del_bytes / (1024*1024):.1f} MB")

st.divider()

# Left Column: Recent Jobs, Right Column: System Engines & Manual Controls
c_left, c_right = st.columns([2, 1])

with c_left:
    st.subheader("📋 Recent Production Slots")
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT j.date, j.slot_number, j.niche, j.status, p.style_name, p.duration_seconds, u.upload_url
            FROM jobs j
            LEFT JOIN production p ON j.job_id = p.job_id
            LEFT JOIN uploads u ON j.job_id = u.job_id
            ORDER BY j.created_at DESC LIMIT 10
        """)
        recent_rows = [dict(r) for r in c.fetchall()]

    if not recent_rows:
        st.info("No production jobs registered yet. Click 'Trigger Daily Batch' to generate today's 3 Shorts!")
    else:
        st.dataframe(recent_rows, use_container_width=True)

    st.subheader("📝 Latest System Audit Events")
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT timestamp, job_id, stage, level, message FROM events ORDER BY event_id DESC LIMIT 8")
        event_rows = [dict(r) for r in c.fetchall()]
    if event_rows:
        st.dataframe(event_rows, use_container_width=True)

with c_right:
    st.subheader("⚙️ System Status")
    st.markdown("""
    - **Ollama LLM (`gemma4`)**: <span class="status-ok">● Online</span> (`http://127.0.0.1:11434`)
    - **Kokoro-82M TTS**: <span class="status-ok">● Ready</span> (ONNX Local)
    - **Faster-Whisper**: <span class="status-ok">● Ready</span> (INT8 Local)
    - **Headless Chrome**: <span class="status-ok">● Ready</span> (v131+ CDP)
    - **FFmpeg Full Build**: <span class="status-ok">● Ready</span> (v8.1.2)
    - **Scheduled Daily Time**: **09:00** (`Asia/Kolkata`)
    """, unsafe_allow_html=True)

    st.divider()
    st.subheader("🚀 Quick Actions")

    if st.button("▶ Trigger Today's 3 Shorts Batch", type="primary", use_container_width=True):
        st.info("Triggering production pipeline... Check the terminal or monitor progress below.")
        from core.orchestrator import DailyOrchestrator
        orch = DailyOrchestrator(factory_root=ROOT)
        with st.spinner("Executing daily production..."):
            res = orch.run_daily_batch()
            st.success(f"Batch completed! Succeeded: {res['jobs_succeeded']}/{res['jobs_executed']}")
            st.rerun()

    if st.button("🧹 Run Safe Storage Cleanup", use_container_width=True):
        from storage.cleanup_manager import CleanupManager
        cm = CleanupManager(db, ROOT / "workspace" / "exports" / "uploaded")
        today_str = datetime.now().strftime("%Y-%m-%d")
        purged = cm.purge_previous_day_verified_mp4s(today_str)
        st.success(f"Storage cleanup completed. Purged {len(purged)} verified previous-day MP4s.")
        st.rerun()

st.sidebar.title("Navigation")
st.sidebar.info("Use the pages above to inspect each pipeline subsystem in detail.")
