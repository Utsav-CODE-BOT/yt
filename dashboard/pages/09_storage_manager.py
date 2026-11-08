"""Safe Storage & Cleanup Manager Page."""

import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database

st.title("🗄️ Safe Storage & Pruning Ledger")

db = Database(ROOT / "workspace" / "factory.db")

with db.get_connection() as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM deletions ORDER BY deleted_at DESC LIMIT 50")
    deletions = [dict(r) for r in c.fetchall()]

st.subheader("Protected Storage Invariants")
st.markdown("""
- **Protected Directories**: `workspace/projects/`, `workspace/research/`, `workspace/scripts/`, `workspace/thumbnails/`, `workspace/logs/`.
- **Protected Files**: Today's active MP4 exports, unverified uploads, SQLite state database.
- **Eligible for Pruning**: Strictly verified uploaded MP4 exports from previous calendar days located in `workspace/exports/uploaded/`.
""")

st.divider()
st.subheader("Verified Deletions Ledger")
if not deletions:
    st.info("No files have been pruned yet. Previous day's verified files will appear here.")
else:
    st.dataframe(deletions, use_container_width=True)
