"""Daily Production Schedule & Timeline Page."""

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("📅 Daily Production (3 Shorts / Day)")

db = Database(ROOT / "workspace" / "factory.db")

selected_date = st.date_input("Select Production Date")
date_str = selected_date.strftime("%Y-%m-%d")

jobs = db.get_jobs_for_date(date_str)

if not jobs:
    st.info(f"No production jobs scheduled or executed yet for {date_str}.")
else:
    st.subheader(f"Slots for {date_str}")
    cols = st.columns(3)
    for idx, job in enumerate(jobs[:3]):
        with cols[idx]:
            st.markdown(f"### Slot {job['slot_number']}")
            st.write(f"**ID**: `{job['job_id']}`")
            st.write(f"**Niche**: {job['niche']}")
            st.write(f"**Pillar**: {job['pillar']}")
            st.write(f"**Status**: `{job['status']}`")

            details = db.get_job_full_details(job["job_id"])
            prod = details.get("production", [{}])[0] if details.get("production") else {}
            if prod:
                st.write(f"**Style**: `{prod.get('style_name')}`")
                st.write(f"**Duration**: {prod.get('duration_seconds', 0.0):.1f}s")
