"""List Gemini models available for the local backend .env API key.

The API key is read from backend/.env and is never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / "backend" / ".env")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    api_key = (dotenv_values(args.env_file).get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        print("GEMINI_API_KEY is not configured.", file=sys.stderr)
        return 2

    url = "https://generativelanguage.googleapis.com/v1beta/models?" + urlencode({"key": api_key})
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            status_code = response.status
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 1

    print(f"status={status_code}")
    if status_code != 200:
        print(body[:1000])
        return 1

    models = json.loads(body).get("models") or []
    usable = [
        model
        for model in models
        if "generateContent" in (model.get("supportedGenerationMethods") or [])
    ]
    for model in usable[: args.limit]:
        print(f"{model.get('name')} | {model.get('displayName')}")
    print(f"usable_count={len(usable)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
