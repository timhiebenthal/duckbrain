"""Minimal Mistral HTTP client for the local RAG experiment."""

import json
import urllib.request
from typing import Any


class MistralClient:
    """Send experiment text to a configured Mistral-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str = "https://api.mistral.ai/v1") -> None:
        if not api_key:
            raise ValueError("A Mistral API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/{endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("Invalid provider response")
        return result

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        data = self.post("embeddings", {"model": model, "input": texts})["data"]
        data = sorted(data, key=lambda row: row["index"])
        vectors = [row["embedding"] for row in data]
        if len(vectors) != len(texts) or any(not v for v in vectors):
            raise ValueError("Provider returned an invalid embedding batch")
        return vectors
