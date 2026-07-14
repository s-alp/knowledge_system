import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from apps.drawing_metadata.services.llm_title_block_classifier import (
    GeminiConfigurationError,
    GeminiResponseError,
    apply_title_block_classifications,
    classify_title_block_candidates,
)


class FakeGeminiResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_classify_title_block_candidates_requires_api_key(settings):
    settings.GEMINI_API_KEY = ""

    with pytest.raises(GeminiConfigurationError):
        classify_title_block_candidates([{"evidence_text": "材質 SUS304"}])


def test_classify_title_block_candidates_posts_json_and_filters_response(settings):
    settings.GEMINI_API_KEY = "test-key"
    settings.GEMINI_MODEL = "gemini-test"
    requests = []

    def fake_urlopen(req, timeout):
        requests.append((req, timeout))
        response_text = json.dumps(
            {
                "classifications": [
                    {"index": 0, "field": "material", "confidence": "high", "reason": "材質欄"},
                    {"index": 99, "field": "material", "confidence": "high", "reason": "範囲外"},
                    {"index": 0, "field": "unknown", "confidence": "high", "reason": "未許可"},
                ]
            }
        )
        return FakeGeminiResponse({"candidates": [{"content": {"parts": [{"text": response_text}]}}]})

    result = classify_title_block_candidates(
        [{"field": None, "value": "SUS304", "evidence_text": "材質 SUS304"}],
        temperature=0.0,
        urlopen=fake_urlopen,
    )

    assert result == [
        {
            "index": 0,
            "field": "material",
            "confidence": "high",
            "reason": "材質欄",
            "source": "gemini_title_block_classifier",
        }
    ]
    req, timeout = requests[0]
    assert timeout == 30
    assert "gemini-test:generateContent" in req.full_url
    body = json.loads(req.data.decode("utf-8"))
    assert body["generationConfig"]["temperature"] == 0.0
    assert body["generationConfig"]["responseMimeType"] == "application/json"


def test_classify_title_block_candidates_reports_http_error_body(settings):
    settings.GEMINI_API_KEY = "test-key"

    def fake_urlopen(req, timeout):
        raise HTTPError(
            req.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=BytesIO(b'{"error":{"message":"JSON mode is not enabled"}}'),
        )

    with pytest.raises(GeminiResponseError, match="JSON mode is not enabled"):
        classify_title_block_candidates(
            [{"field": None, "value": "SUS304", "evidence_text": "材質 SUS304"}],
            urlopen=fake_urlopen,
        )


def test_apply_title_block_classifications_adds_missing_field_without_overwrite():
    canonical = {
        "title_block_fields": {"drawing_name": "SUS304"},
        "title_block_candidates": [
            {
                "field": "drawing_name",
                "label": "図面名",
                "value": "SUS304",
                "confidence": "medium",
                "evidence_text": "品名 SUS304",
            }
        ],
    }

    result = apply_title_block_classifications(
        canonical,
        [{"index": 0, "field": "material", "confidence": "high", "reason": "材質値に見える"}],
    )

    assert result["title_block_fields"]["drawing_name"] == "SUS304"
    assert result["title_block_fields"]["material"] == "SUS304"
    assert result["title_block_candidates"][0]["llm_field"] == "material"
    assert result["title_block_candidates"][0]["llm_confidence"] == "high"
    assert result["title_block_llm_classifications"][0]["accepted_as_field"] is True


def test_apply_title_block_classifications_does_not_accept_label_only_value():
    canonical = {
        "title_block_fields": {},
        "title_block_candidates": [
            {
                "field": "drawing_name",
                "label": "図面名",
                "value": "材質",
                "confidence": "low",
                "evidence_text": "材質",
            }
        ],
    }

    result = apply_title_block_classifications(
        canonical,
        [{"index": 0, "field": "material", "confidence": "high", "reason": "ラベルのみ"}],
    )

    assert "material" not in result["title_block_fields"]
    assert result["title_block_candidates"][0]["llm_field"] == "material"
    assert result["title_block_llm_classifications"][0]["accepted_as_field"] is False
