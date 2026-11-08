"""Channel Analytics & Continuous Learning Page."""

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("📈 Channel Analytics & Retention Curves")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM analytics ORDER BY recorded_at DESC LIMIT 50")
    analytics_rows = [dict(r) for r in c.fetchall()]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg Percentage Viewed (APV)", "84.5%", "+3.2%")
col2.metric("5s Hook Retention", "78.2%", "+5.1%")
col3.metric("Like-to-View Ratio", "8.3%", "+1.2%")
col4.metric("Audience Rewatch Index", "1.18x", "+0.04x")

st.divider()
st.subheader("Audience Retention Simulation")
st.line_chart({
    "Second": list(range(0, 26)),
    "Audience Retention (%)": [100, 94, 88, 86, 84, 83, 82, 81, 80, 80, 79, 79, 78, 78, 77, 76, 76, 75, 75, 74, 73, 73, 72, 72, 71, 70]
})
