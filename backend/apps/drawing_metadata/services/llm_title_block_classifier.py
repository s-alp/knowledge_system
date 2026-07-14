from __future__ import annotations

import json
from typing import Callable
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from django.conf import settings

from apps.drawing_metadata.services.normalization import TITLE_BLOCK_FIELD_RULES


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiResponseError(RuntimeError):
    pass


UrlOpen = Callable[..., object]


def classify_title_block_candidates(
    candidates: list[dict],
    *,
    api_key: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    urlopen: UrlOpen | None = None,
) -> list[dict]:
    """Classify existing title-block candidates without inventing values."""
    if not candidates:
        return []

    api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
    if not api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY is not configured.")

    model = model or settings.GEMINI_MODEL
    temperature = settings.GEMINI_TEMPERATURE if temperature is None else temperature
    urlopen = urlopen or request.urlopen

    payload = _build_request_payload(candidates, temperature)
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(model, safe='')}:generateContent?key={quote(api_key, safe='')}"
    )
    req = request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        response = urlopen(req, timeout=30)
        body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise GeminiResponseError(f"Gemini API returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise GeminiResponseError(f"Gemini API request failed: {exc.reason}") from exc

    return _parse_response(body, len(candidates))


def _build_request_payload(candidates: list[dict], temperature: float) -> dict:
    prompt = {
        "task": "Classify existing ICAD title-block text candidates into allowed fields.",
        "rules": [
            "Return JSON only.",
            "Do not invent values.",
            "Use only the candidate index and allowed field names.",
            "If a candidate is only a label or is ambiguous, use field=null and confidence='low'.",
        ],
        "allowed_fields": sorted(TITLE_BLOCK_FIELD_RULES.keys()),
        "candidates": [
            {
                "index": index,
                "field_hint": candidate.get("field"),
                "value": candidate.get("value"),
                "evidence_text": candidate.get("evidence_text"),
                "view_name": candidate.get("view_name"),
                "layer_no": candidate.get("layer_no"),
                "inside_print_area": candidate.get("inside_print_area"),
            }
            for index, candidate in enumerate(candidates)
        ],
        "response_schema": {
            "classifications": [
                {
                    "index": 0,
                    "field": "material",
                    "confidence": "high|medium|low",
                    "reason": "short reason",
                }
            ]
        },
    }
    return {
        "contents": [{"role": "user", "parts": [{"text": json.dumps(prompt, ensure_ascii=False)}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }


def _parse_response(body: str, candidate_count: int) -> list[dict]:
    try:
        payload = json.loads(body)
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise GeminiResponseError("Gemini API response did not contain valid JSON classifications.") from exc

    classifications = parsed.get("classifications")
    if not isinstance(classifications, list):
        raise GeminiResponseError("Gemini API JSON response is missing classifications.")

    allowed_fields = set(TITLE_BLOCK_FIELD_RULES.keys())
    accepted: list[dict] = []
    for item in classifications:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        field = item.get("field")
        if not isinstance(index, int) or index < 0 or index >= candidate_count:
            continue
        if field is not None and field not in allowed_fields:
            continue
        confidence = item.get("confidence")
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        accepted.append(
            {
                "index": index,
                "field": field,
                "confidence": confidence,
                "reason": str(item.get("reason") or ""),
                "source": "gemini_title_block_classifier",
            }
        )
    return accepted
