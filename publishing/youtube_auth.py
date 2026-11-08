"""YouTube OAuth 2.0 Authentication Manager for Autonomous Faceless Shorts Factory.

Handles token refresh, credentials persistence, and non-interactive daemon authorization.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("factory.youtube_auth")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeAuth:
    """Manages YouTube Data API v3 OAuth credentials."""

    def __init__(self, credentials_dir: str | Path = r"C:\Users\ud127\faceless-shorts-factory\credentials"):
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.client_secrets_path = self.credentials_dir / "client_secrets.json"
        self.token_path = self.credentials_dir / "token.json"

    def is_authenticated(self) -> bool:
        """Check if active valid token exists."""
        if not self.token_path.exists():
            return False
        try:
            data = json.loads(self.token_path.read_text(encoding="utf-8"))
            return "refresh_token" in data or "access_token" in data
        except Exception:
            return False

    def get_access_token(self) -> Optional[str]:
        """Retrieve or refresh OAuth access token."""
        if not self.token_path.exists():
            logger.warning("No token.json found in %s.", self.credentials_dir)
            return None

        try:
            token_data = json.loads(self.token_path.read_text(encoding="utf-8"))
            refresh_token = token_data.get("refresh_token")

            # If client_secrets exists, refresh the token
            if refresh_token and self.client_secrets_path.exists():
                secrets = json.loads(self.client_secrets_path.read_text(encoding="utf-8"))
                installed = secrets.get("installed") or secrets.get("web", {})
                client_id = installed.get("client_id")
                client_secret = installed.get("client_secret")

                if client_id and client_secret:
                    token_url = "https://oauth2.googleapis.com/token"
                    params = urllib.parse.urlencode({
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    }).encode("utf-8")

                    req = urllib.request.Request(token_url, data=params, headers={"Content-Type": "application/x-www-form-urlencoded"})
                    with urllib.request.urlopen(req, timeout=10.0) as resp:
                        fresh = json.loads(resp.read().decode("utf-8"))
                        token_data["access_token"] = fresh.get("access_token")
                        self.token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
                        return token_data["access_token"]

            return token_data.get("access_token")
        except Exception as e:
            logger.error("Error obtaining YouTube access token: %s", e)
            return None
