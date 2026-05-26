#!/bin/bash
# Initial environment setup for knowledge-system-screenshot.
# Installs Playwright + Chromium Headless Shell *inside the bash sandbox*
# (Windows-mounted folders cannot execute Chromium binaries reliably.)
set -e
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR=/tmp/ks-screenshot

echo "[setup] skill dir : $SKILL_DIR"
echo "[setup] runtime   : $RUNTIME_DIR"

mkdir -p "$RUNTIME_DIR"
cd "$RUNTIME_DIR"

# package.json
if [ ! -f package.json ]; then
  npm init -y >/dev/null 2>&1
fi

# playwright
if [ ! -d node_modules/playwright ]; then
  echo "[setup] installing playwright (npm)"
  npm install playwright --silent
else
  echo "[setup] playwright already installed in $RUNTIME_DIR"
fi

# chromium-headless-shell (cached in default location ~/.cache/ms-playwright)
if [ -z "$(find /sessions/*/.cache/ms-playwright/ -maxdepth 1 -name 'chromium_headless_shell-*' -print -quit 2>/dev/null)" ]; then
  echo "[setup] installing chromium-headless-shell"
  npx playwright install chromium-headless-shell
else
  echo "[setup] chromium-headless-shell already cached"
fi

# Ensure .env exists in skill folder
if [ ! -f "$SKILL_DIR/.env" ] && [ -f "$SKILL_DIR/.env.example" ]; then
  cp "$SKILL_DIR/.env.example" "$SKILL_DIR/.env"
  echo "[setup] .env created from .env.example — KNOW_PW を編集してください"
fi

# Output dir
mkdir -p "$SKILL_DIR/screenshots"

echo "[setup] complete. Next: edit $SKILL_DIR/.env then run 'bash run.sh'."
