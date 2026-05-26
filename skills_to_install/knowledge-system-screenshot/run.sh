#!/bin/bash
# Run the screenshot grabber. Runtime is /tmp/ks-screenshot (set up by setup.sh).
set -e
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR=/tmp/ks-screenshot

if [ ! -d "$RUNTIME_DIR/node_modules/playwright" ]; then
  echo "[run] runtime not found. Running setup.sh first..."
  bash "$SKILL_DIR/setup.sh"
fi

cd "$RUNTIME_DIR"
KS_SKILL_DIR="$SKILL_DIR" node "$SKILL_DIR/grab_screenshots.js"
