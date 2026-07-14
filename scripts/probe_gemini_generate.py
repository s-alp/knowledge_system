"""Probe Gemini generateContent availability for candidate models.

The API key is read from backend/.env and is never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]


def _post_json(url: str, payload: dict) -> tuple[int, str]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 0, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / "backend" / ".env")
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    args = parser.parse_args()

    api_key = (dotenv_values(args.env_file).get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        print("GEMINI_API_KEY is not configured.", file=sys.stderr)
        return 2

    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Return only OK."}]}],
        "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
    }
    ok = False
    for model in args.models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?"
            + urlencode({"key": api_key})
        )
        status, body = _post_json(url, payload)
        if status == 200:
            ok = True
            print(f"{model}: OK")
            continue
        message = body
        try:
            message = json.loads(body).get("error", {}).get("message", body)
        except json.JSONDecodeError:
            pass
        print(f"{model}: HTTP {status}: {str(message)[:240]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
