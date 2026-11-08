"""Research & Fact Verification Audit Page."""

import streamlit as st
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("🔬 Research & Fact Verification Audits")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM research ORDER BY created_at DESC LIMIT 30")
    records = [dict(r) for r in c.fetchall()]

if not records:
    st.info("No research records logged in database yet.")
else:
    for r in records:
        status = "✅ PASSED" if r["passed_verification"] else "⚠️ FLAGGED"
        with st.expander(f"{r['research_id']} (Job: {r['job_id']}) - {status}"):
            st.write(f"Report Path: `{r['report_path']}`")
            if r.get("report_path") and Path(r["report_path"]).exists():
                st.markdown(Path(r["report_path"]).read_text(encoding="utf-8"))
