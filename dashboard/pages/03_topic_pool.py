"""Topic Pool & Intelligence Page."""

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("💡 Topic Candidate Pool & Deduplication")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM topics ORDER BY created_at DESC LIMIT 50")
    topics = [dict(r) for r in c.fetchall()]

if not topics:
    st.info("No topic candidates stored in database yet.")
else:
    st.dataframe(topics, use_container_width=True)
