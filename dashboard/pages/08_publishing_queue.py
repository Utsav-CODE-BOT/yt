"""Publishing Queue & Upload Verification Page."""

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("📤 YouTube Publishing Queue & Upload Ledger")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM uploads ORDER BY uploaded_at DESC LIMIT 30")
    uploads = [dict(r) for r in c.fetchall()]

if not uploads:
    st.info("No uploads recorded in database yet.")
else:
    for u in uploads:
        status_badge = "🟢 VERIFIED LIVE" if u["upload_status"] == "VERIFIED" else f"🟡 {u['upload_status']}"
        with st.expander(f"{u['youtube_title']} - {status_badge}"):
            st.write(f"**Job ID**: `{u['job_id']}`")
            st.write(f"**Video ID**: `{u['video_id']}`")
            st.write(f"**Watch URL**: [{u['upload_url']}]({u['upload_url']})")
            st.write(f"**Uploaded At**: {u['uploaded_at']}")
            st.write(f"**Verified At**: {u.get('verified_at', 'Pending')}")
            st.text_area("Description", u["youtube_description"], height=100)
