from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--source-kind", required=True, choices=["2d", "3d"])
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--sxnet-dll-path", required=True)
    parser.add_argument("--icad-executable-path", required=False)
    parser.add_argument("--icad-startup-wait-seconds", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    args = parser.parse_args()

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        args.runner,
        "extract",
        "--input-path",
        args.input_path,
        "--source-kind",
        args.source_kind,
        "--output-path",
        args.output_path,
        "--sxnet-dll-path",
        args.sxnet_dll_path,
    ]
    if args.icad_executable_path:
        command.extend(
            [
                "--icad-executable-path",
                args.icad_executable_path,
                "--icad-startup-wait-seconds",
                str(args.icad_startup_wait_seconds),
            ]
        )

    print("COMMAND:", command)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=args.timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"TIMEOUT: {args.timeout_seconds}s")
        print("STDOUT:", exc.stdout)
        print("STDERR:", exc.stderr)
        return 124

    print("RETURN_CODE:", completed.returncode)
    print("STDOUT:", completed.stdout)
    print("STDERR:", completed.stderr)
    print("OUTPUT_EXISTS:", output_path.exists())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
