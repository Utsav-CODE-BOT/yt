"""Pipeline Status Dashboard Page."""

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("🔄 Pipeline Status & State Machine")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 20")
    jobs = [dict(r) for r in c.fetchall()]

if not jobs:
    st.info("No jobs recorded in pipeline yet.")
else:
    for job in jobs:
        with st.expander(f"Job: {job['job_id']} | Status: {job['status']} | Niche: {job['niche']}", expanded=False):
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Date**: {job['date']}")
            col1.write(f"**Slot Number**: {job['slot_number']}")
            col2.write(f"**Current Step**: {job['current_step']}")
            col2.write(f"**Retry Count**: {job['retry_count']} / {job['max_retries']}")
            col3.write(f"**Created At**: {job['created_at']}")
            col3.write(f"**Updated At**: {job['updated_at']}")
            if job.get("error_message"):
                st.error(f"Error Message: {job['error_message']}")
