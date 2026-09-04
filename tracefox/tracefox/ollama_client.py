from __future__ import annotations

import json
from typing import Any

import httpx

OLLAMA_BASE = "http://127.0.0.1:11434"


async def list_models() -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            response.raise_for_status()
            payload = response.json()
        names = []
        for model in payload.get("models", []):
            name = model.get("name") or model.get("model")
            if name:
                names.append(name)
        return names
    except Exception:
        return []


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    meta = result.get("metadata") or {}
    return {
        "site": result.get("site"),
        "category": result.get("category"),
        "url": result.get("profile_url"),
        "title": meta.get("title"),
        "description": meta.get("description"),
        "canonical": meta.get("canonical"),
        "username_visible": meta.get("username_visible"),
    }


async def analyze_results(username: str, model: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    found = [_compact_result(r) for r in results if r.get("status") == "found"]
    prompt_results = found[:160]
    prompt = f"""
You are TraceFox's local correlation analyst. Analyze PUBLIC username-search results only.
The searched username is: {username!r}

Important rules:
- A shared username alone is weak evidence that accounts belong to the same person.
- Do not invent names, locations, emails, phone numbers, or relationships.
- Only use evidence present in the supplied profile metadata.
- Explicitly call out collisions and contradictory metadata.
- Return STRICT JSON, no markdown.

Return this structure:
{{
  "summary": "short plain-language overview",
  "collision_risk": "low|medium|high",
  "clusters": [
    {{
      "label": "short descriptive label",
      "confidence": 0,
      "sites": ["site names"],
      "evidence": ["specific shared clues"],
      "conflicts": ["specific contradictory clues"]
    }}
  ],
  "outliers": ["site names that do not fit a cluster"],
  "notes": ["important limitations"]
}}

Public profile results:
{json.dumps(prompt_results, ensure_ascii=False)}
""".strip()

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": "You are a careful OSINT correlation assistant that never treats a username match as identity proof."},
                    {"role": "user", "content": prompt},
                ],
                "options": {"temperature": 0.15},
            },
        )
        response.raise_for_status()
        payload = response.json()

    raw = payload.get("message", {}).get("content") or payload.get("response") or "{}"
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Ollama returned non-object JSON")
        return parsed
    except Exception:
        return {
            "summary": raw[:4000],
            "collision_risk": "unknown",
            "clusters": [],
            "outliers": [],
            "notes": ["The selected Ollama model did not return valid structured JSON."],
        }
