from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import request


BOUNDARY = "----CodexLocalUploadBoundary"


def build_multipart_body(field_name: str, filename: str, content_type: str, payload: bytes) -> bytes:
    lines = [
        f"--{BOUNDARY}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
        payload,
        b"\r\n",
        f"--{BOUNDARY}--\r\n".encode("utf-8"),
    ]
    return b"".join(lines)


def post_file(url: str, filename: str, content_type: str, payload: bytes) -> dict:
    body = build_multipart_body("file", filename, content_type, payload)
    req = request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    api_base_url = os.getenv("CHECK_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
    pdf_payload = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    stl_payload = Path("tests/fixtures/sample.stl").read_bytes()

    pdf_result = post_file(
        f"{api_base_url}/viewer2d/upload",
        "sample.pdf",
        "application/pdf",
        pdf_payload,
    )
    stl_result = post_file(
        f"{api_base_url}/viewer3d/upload",
        "sample.stl",
        "model/stl",
        stl_payload,
    )

    print(
        json.dumps(
            {
                "apiBaseUrl": api_base_url,
                "pdf": {
                    "filename": pdf_result.get("filename"),
                    "extension": pdf_result.get("extension"),
                    "pageCount": pdf_result.get("pageCount"),
                },
                "stl": {
                    "filename": stl_result.get("filename"),
                    "status": stl_result.get("status"),
                    "sourceExtension": stl_result.get("sourceExtension"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
