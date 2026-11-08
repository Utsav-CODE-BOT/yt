"""System Settings & Niche Configuration Page."""

import streamlit as st
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.title("⚙️ System Settings & Configuration")

settings_path = ROOT / "settings.yaml"

if not settings_path.exists():
    st.error("settings.yaml not found at root directory.")
else:
    content = settings_path.read_text(encoding="utf-8")
    config = yaml.safe_load(content)

    st.subheader("Scheduling & Automation")
    st.write(f"**Target Time**: `{config.get('production', {}).get('daily_schedule_time', '09:00')}`")
    st.write(f"**Timezone**: `{config.get('production', {}).get('timezone', 'Asia/Kolkata')}`")
    st.write(f"**Videos Per Day**: `{config.get('production', {}).get('videos_per_day', 3)}`")
    st.write(f"**Target Duration**: `{config.get('production', {}).get('target_duration_seconds', 25)}s` (Acceptable: 22-28s)")

    st.divider()
    st.subheader("Raw settings.yaml Editor")
    new_text = st.text_area("Edit Configuration", content, height=450)
    if st.button("Save Settings", type="primary"):
        try:
            yaml.safe_load(new_text)  # validate syntax
            settings_path.write_text(new_text, encoding="utf-8")
            st.success("Settings saved successfully!")
        except Exception as e:
            st.error(f"Invalid YAML syntax: {e}")
