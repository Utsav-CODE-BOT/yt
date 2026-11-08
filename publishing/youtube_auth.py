"""YouTube OAuth 2.0 Authentication Manager for Autonomous Faceless Shorts Factory.

Handles token refresh, credentials persistence, interactive OAuth login,
and non-interactive daemon authorization.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
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
        self.token_path = self.credentials_dir / "token.json"

    def find_client_secrets(self) -> Optional[Path]:
        """Locates client_secret.json or client_secrets.json in credentials directory."""
        for candidate in ["client_secret.json", "client_secrets.json"]:
            p = self.credentials_dir / candidate
            if p.exists():
                return p
        for p in self.credentials_dir.glob("client_secret*.json"):
            if not p.name.endswith(".sample.json"):
                return p
        return None

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
            secrets_path = self.find_client_secrets()

            # If client_secrets exists, refresh the token automatically
            if refresh_token and secrets_path:
                secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
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

                    req = urllib.request.Request(
                        token_url,
                        data=params,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                    with urllib.request.urlopen(req, timeout=10.0) as resp:
                        fresh = json.loads(resp.read().decode("utf-8"))
                        token_data["access_token"] = fresh.get("access_token")
                        self.token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
                        return token_data["access_token"]

            return token_data.get("access_token")
        except Exception as e:
            logger.error("Error obtaining YouTube access token: %s", e)
            return None

    def interactive_login(self, port: int = 8080) -> bool:
        """Runs a one-time interactive OAuth 2.0 flow to generate credentials/token.json."""
        secrets_path = self.find_client_secrets()
        if not secrets_path:
            print("\n[!] Error: No client_secret.json found in credentials directory!")
            print(f"Please place your Google Cloud OAuth Client JSON in:\n{self.credentials_dir}\\client_secret.json\n")
            return False

        try:
            secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
            installed = secrets.get("installed") or secrets.get("web", {})
            client_id = installed.get("client_id")
            client_secret = installed.get("client_secret")
        except Exception as e:
            print(f"[!] Failed to parse {secrets_path}: {e}")
            return False

        if not client_id or not client_secret:
            print(f"[!] client_id or client_secret missing in {secrets_path}")
            return False

        redirect_uri = f"http://localhost:{port}/"
        scope_str = " ".join(SCOPES)
        auth_params = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope_str,
            "access_type": "offline",
            "prompt": "consent",
        })
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{auth_params}"

        auth_code_holder: Dict[str, Optional[str]] = {"code": None, "error": None}

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)

                if "code" in query:
                    auth_code_holder["code"] = query["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = (
                        "<html><body style='font-family:sans-serif;text-align:center;padding:50px;'>"
                        "<h2 style='color:#16a34a;'>✅ YouTube Authorization Successful!</h2>"
                        "<p>Your factory token has been acquired. You can close this tab and return to the terminal.</p>"
                        "</body></html>"
                    )
                    self.wfile.write(html.encode("utf-8"))
                elif "error" in query:
                    auth_code_holder["error"] = query["error"][0]
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Authorization Denied</h2></body></html>")
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress HTTP server noise

        server = HTTPServer(("localhost", port), OAuthCallbackHandler)
        server.timeout = 180  # 3 minute timeout

        print("\n=======================================================")
        print("  YouTube Channel One-Time OAuth Authorization")
        print("=======================================================")
        print(f"Opening your default browser to connect your YouTube account...")
        print(f"If the browser doesn't open automatically, visit this URL:\n\n{auth_url}\n")
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

        print(f"Waiting for authorization on {redirect_uri} (Timeout: 3 minutes)...")
        while auth_code_holder["code"] is None and auth_code_holder["error"] is None:
            server.handle_request()

        server.server_close()

        code = auth_code_holder["code"]
        if not code:
            print(f"\n[!] Authorization failed or timed out: {auth_code_holder.get('error')}")
            return False

        print("\nAuthorization code received! Exchanging for permanent refresh token...")
        token_url = "https://oauth2.googleapis.com/token"
        token_params = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }).encode("utf-8")

        req = urllib.request.Request(
            token_url,
            data=token_params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
                self.token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
                print(f"[+] Token successfully saved to: {self.token_path}")
                print("YouTube channel authentication is now complete and permanent for autonomous daily uploads!\n")
                return True
        except Exception as e:
            print(f"[!] Failed to exchange code for token: {e}")
            return False
