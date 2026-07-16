from __future__ import annotations

import json
from typing import Callable
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from django.conf import settings

from apps.drawing_metadata.services.normalization import TITLE_BLOCK_FIELD_RULES, _is_title_block_value_usable


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiResponseError(RuntimeError):
    pass


UrlOpen = Callable[..., object]


def has_replacement_character(candidate: dict) -> bool:
    """Return true when a candidate still contains lost-character markers."""
    values = [
        candidate.get("field"),
        candidate.get("value"),
        candidate.get("evidence_text"),
        candidate.get("view_name"),
    ]
    return any("\ufffd" in str(value) for value in values if value is not None)


def filter_classifiable_title_block_candidates(candidates: list[dict]) -> tuple[list[dict], list[int]]:
    """Filter LLM inputs while keeping a map back to the original candidate list."""
    classifiable, original_indexes, _stats = filter_classifiable_title_block_candidates_with_stats(candidates)
    return classifiable, original_indexes


def filter_classifiable_title_block_candidates_with_stats(candidates: list[dict]) -> tuple[list[dict], list[int], dict]:
    """Filter LLM inputs while reporting why unsafe or unhelpful candidates were skipped."""
    classifiable: list[dict] = []
    original_indexes: list[int] = []
    stats = {
        "replacement_character": 0,
        "unusable_value": 0,
    }
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        if has_replacement_character(candidate):
            stats["replacement_character"] += 1
            continue
        if not _is_candidate_value_classifiable(candidate):
            stats["unusable_value"] += 1
            continue
        classifiable.append(candidate)
        original_indexes.append(index)
    return classifiable, original_indexes, stats


def _is_candidate_value_classifiable(candidate: dict) -> bool:
    field = candidate.get("field")
    rule = TITLE_BLOCK_FIELD_RULES.get(str(field), {}) if field else {}
    max_value_length = int(rule.get("max_value_length", 80))
    return _is_title_block_value_usable(candidate.get("value"), max_length=max_value_length)


def remap_title_block_classification_indexes(classifications: list[dict], original_indexes: list[int]) -> list[dict]:
    """Convert LLM result indexes back to the canonical title_block_candidates indexes."""
    remapped: list[dict] = []
    for classification in classifications:
        if not isinstance(classification, dict):
            continue
        filtered_index = classification.get("index")
        if not isinstance(filtered_index, int) or filtered_index < 0 or filtered_index >= len(original_indexes):
            continue
        item = dict(classification)
        item["index"] = original_indexes[filtered_index]
        remapped.append(item)
    return remapped


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
    errors: list[str] = []
    for candidate_model in _gemini_models_to_try(model):
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(candidate_model, safe='')}:generateContent?key={quote(api_key, safe='')}"
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
            return _parse_response(body, len(candidates))
        except GeminiResponseError as exc:
            errors.append(f"{candidate_model}: invalid response: {exc}")
        except HTTPError as exc:
            message = f"{candidate_model}: HTTP {exc.code}: {_read_error_body(exc)}"
            errors.append(message)
            if not _is_retryable_gemini_http_error(exc.code):
                raise GeminiResponseError(message) from exc
        except (TimeoutError, URLError, OSError) as exc:
            errors.append(f"{candidate_model}: request failed: {exc}")

    raise GeminiResponseError("Gemini API request failed for all configured models: " + " | ".join(errors))


def _gemini_models_to_try(primary_model: str) -> list[str]:
    fallback_models = getattr(settings, "GEMINI_FALLBACK_MODELS", [])
    models = [primary_model, *fallback_models]
    ordered: list[str] = []
    for model in models:
        if model and model not in ordered:
            ordered.append(model)
    return ordered


def _is_retryable_gemini_http_error(status_code: int) -> bool:
    return status_code in {404, 429, 503, 504}


def _read_error_body(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return "no response body"
    if not body:
        return "empty response body"
    return body[:500]


def apply_title_block_classifications(canonical_attributes: dict, classifications: list[dict]) -> dict:
    """Apply Gemini labels to existing candidates without overwriting rule-based fields."""
    if not classifications:
        return canonical_attributes

    candidates = canonical_attributes.get("title_block_candidates") or []
    if not isinstance(candidates, list):
        return canonical_attributes

    fields = dict(canonical_attributes.get("title_block_fields") or {})
    applied: list[dict] = []
    allowed_confidences = {"high", "medium", "low"}

    for classification in classifications:
        if not isinstance(classification, dict):
            continue
        index = classification.get("index")
        if not isinstance(index, int) or index < 0 or index >= len(candidates):
            continue

        candidate = candidates[index]
        if not isinstance(candidate, dict):
            continue

        field = classification.get("field")
        if field is not None and field not in TITLE_BLOCK_FIELD_RULES:
            continue
        confidence = classification.get("confidence")
        if confidence not in allowed_confidences:
            confidence = "low"
        source = classification.get("source") or "gemini_title_block_classifier"
        reason = str(classification.get("reason") or "")

        candidate["llm_field"] = field
        candidate["llm_confidence"] = confidence
        candidate["llm_reason"] = reason
        candidate["llm_source"] = source

        value = candidate.get("value")
        accepted_as_field = False
        inside_print_area = candidate.get("inside_print_area")
        if field and confidence in {"high", "medium"} and field not in fields and inside_print_area is not False:
            rule = TITLE_BLOCK_FIELD_RULES.get(field, {})
            max_value_length = int(rule.get("max_value_length", 80))
            if _is_title_block_value_usable(value, max_length=max_value_length):
                fields[field] = value
                accepted_as_field = True

        applied.append(
            {
                "index": index,
                "field": field,
                "confidence": confidence,
                "reason": reason,
                "source": source,
                "value": value,
                "accepted_as_field": accepted_as_field,
            }
        )

    canonical_attributes["title_block_fields"] = fields
    canonical_attributes["title_block_llm_classifications"] = applied
    return canonical_attributes


def _build_request_payload(candidates: list[dict], temperature: float) -> dict:
    prompt = {
        "task": "Classify existing ICAD title-block text candidates into allowed fields.",
        "rules": [
            "Return JSON only.",
            "Do not invent values.",
            "Use only the candidate index and allowed field names.",
            "If candidate.value is null or empty, use field=null and confidence='low'.",
            "If a candidate is only a label or is ambiguous, use field=null and confidence='low'.",
            "Reference or source drawing numbers such as 参考図番 or 元図 are not the current drawing_number.",
            "Stock shape or dimensions without a material grade are not a material value.",
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
