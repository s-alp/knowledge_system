import json

import pytest

from apps.drawing_metadata.services.llm_title_block_classifier import (
    GeminiConfigurationError,
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
