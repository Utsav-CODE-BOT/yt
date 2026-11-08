"""Script Lab Page."""

import streamlit as st
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("✍️ Script Lab & Retention Inspector")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM scripts ORDER BY created_at DESC LIMIT 30")
    scripts = [dict(r) for r in c.fetchall()]

if not scripts:
    st.info("No scripts generated in database yet.")
else:
    for s in scripts:
        with st.expander(f"Script {s['script_id']} (Job: {s['job_id']}) - {s['word_count']} words | {s['estimated_duration']:.1f}s", expanded=False):
            st.markdown(f"**Chosen Hook**: *\"{s['chosen_hook']}\"*")
            st.markdown(f"**Full Narration Script**:\n> {s['script_text']}")
            col1, col2 = st.columns(2)
            col1.write(f"Word Count: {s['word_count']}")
            col2.write(f"Estimated Duration: {s['estimated_duration']:.1f}s")
