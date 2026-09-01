#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
OUTPUT="$BACKEND_DIR/future-you-backend.zip"
BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/future-you-lambda.XXXXXX")"

cleanup() {
  rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

"$BACKEND_DIR/.venv/bin/python" -m pip install \
  --requirement "$BACKEND_DIR/requirements-lambda.txt" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target "$BUILD_DIR"

cp -R "$BACKEND_DIR/app" "$BUILD_DIR/app"
cp -R "$PROJECT_DIR/agent" "$BUILD_DIR/agent"

find "$BUILD_DIR" -type d \( -name __pycache__ -o -name tests \) -prune -exec rm -rf {} +
find "$BUILD_DIR" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete

TEMP_OUTPUT="$BUILD_DIR.zip"
(
  cd "$BUILD_DIR"
  zip -qr "$TEMP_OUTPUT" .
)
mv "$TEMP_OUTPUT" "$OUTPUT"

unzip -tq "$OUTPUT" >/dev/null
MANIFEST="$BUILD_DIR/manifest.txt"
unzip -Z1 "$OUTPUT" > "$MANIFEST"
for required in app/lambda_handler.py app/main.py agent/__init__.py; do
  if ! grep -Fxq "$required" "$MANIFEST"; then
    echo "Lambda package is missing $required" >&2
    exit 1
  fi
done

echo "Built $OUTPUT"
