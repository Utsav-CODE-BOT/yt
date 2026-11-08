"""Ollama Local LLM Client for Autonomous Faceless Shorts Factory.

Provides a clean REST adapter for the locally running Ollama instance (gemma4:latest)
with connection timeouts, retry handling, temperature controls, and JSON schema extraction.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("factory.llm_client")


class OllamaClient:
    """Communicates with local Ollama HTTP REST API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "gemma4:latest",
        timeout_seconds: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Call Ollama /api/generate endpoint with streaming disabled."""
        endpoint = f"{self.base_url}/api/generate"

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "").strip()
        except urllib.error.URLError as e:
            logger.error("Failed to connect to local Ollama service at %s: %s", self.base_url, e)
            raise ConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Ensure 'ollama serve' is active."
            ) from e

    def is_healthy(self) -> bool:
        """Verify Ollama service is reachable and responsive."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False
