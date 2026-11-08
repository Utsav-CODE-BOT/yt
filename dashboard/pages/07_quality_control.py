"""Quality Control Gate Dashboard Page."""

import streamlit as st
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("🛡️ Quality Control & Compliance Gates")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM quality_checks ORDER BY created_at DESC LIMIT 20")
    checks = [dict(r) for r in c.fetchall()]

if not checks:
    st.info("No quality checks recorded in database yet.")
else:
    for qc in checks:
        status_label = "✅ APPROVED" if qc["passed"] else "❌ REJECTED"
        with st.expander(f"QC: {qc['qc_id']} (Job: {qc['job_id']}) - Score: {qc['overall_score']:.1f}/100 [{status_label}]"):
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"Resolution Check: {'✅' if qc['resolution_check'] else '❌'}")
            col2.write(f"Duration Check: {'✅' if qc['duration_check'] else '❌'}")
            col3.write(f"Audio Levels Check: {'✅' if qc['audio_levels_check'] else '❌'}")
            col4.write(f"Caption Sync Check: {'✅' if qc['caption_sync_check'] else '❌'}")

            if qc.get("qc_report_json"):
                rep = json.loads(qc["qc_report_json"])
                if rep.get("issues"):
                    st.warning("Issues Detected: " + ", ".join(rep["issues"]))
