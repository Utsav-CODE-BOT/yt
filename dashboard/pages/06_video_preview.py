"""Video Preview & Contact Sheet Gallery Page."""

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("🎥 Video Preview & Visual Contact Sheets")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM production ORDER BY created_at DESC LIMIT 15")
    prods = [dict(r) for r in c.fetchall()]

if not prods:
    st.info("No rendered video productions available yet.")
else:
    for p in prods:
        st.subheader(f"Job: {p['job_id']} · Style: {p['style_name']} ({p['duration_seconds']:.1f}s)")
        mp4_path = Path(p["render_mp4_path"])
        sheet_path = Path(p["project_dir"]) / "review" / "all.jpg"

        col1, col2 = st.columns([1, 1])
        with col1:
            if sheet_path.exists():
                st.image(str(sheet_path), caption="Contact Sheet (all.jpg)", use_container_width=True)
            else:
                st.warning("Contact sheet not found.")
        with col2:
            if mp4_path.exists():
                st.video(str(mp4_path))
            else:
                st.info(f"Video export: {mp4_path.name} (Pruned or moved to uploads)")
        st.divider()
