#!/usr/bin/env bash

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

if [[ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
  echo "Error: backend/.venv/bin/uvicorn was not found. Install the backend dependencies as described in the README." >&2
  exit 1
fi

if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/vite" ]]; then
  echo "Error: frontend dependencies were not found. Run npm install in the frontend directory." >&2
  exit 1
fi

port_is_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

if port_is_in_use 8000; then
  echo "Error: port 8000 is already in use. Stop the existing backend process and try again." >&2
  exit 1
fi

if port_is_in_use 5173; then
  echo "Error: port 5173 is already in use. Stop the existing frontend process and try again." >&2
  exit 1
fi

# start-dev.sh is the AWS-free entry point. start-aws.sh marks its validated
# environment before delegating to this shared process runner.
if [[ "${FUTURE_YOU_RUNTIME_PROFILE:-mock}" == "mock" ]]; then
  export AUTH_MODE=mock
  export DATA_SOURCE=mock
  export AI_MODE=mock
  export VITE_AUTH_MODE=mock
elif [[ "${FUTURE_YOU_RUNTIME_PROFILE}" != "aws" ]]; then
  echo "Error: FUTURE_YOU_RUNTIME_PROFILE must be 'mock' or 'aws'." >&2
  exit 1
fi
export VITE_API_URL="${VITE_API_URL:-http://127.0.0.1:8000}"
export PYTHONPATH="$PROJECT_DIR:$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Manage-mode previews must be signed before they can be confirmed. The AWS launcher
# requires a persistent key; the Mock launcher can safely use an ephemeral one.
if [[ -z "${AGENT_PROPOSAL_SIGNING_KEY:-}" ]]; then
  if ! command -v openssl >/dev/null 2>&1; then
    echo "Error: openssl is required to generate the local proposal signing key." >&2
    exit 1
  fi
  AGENT_PROPOSAL_SIGNING_KEY="$(openssl rand -hex 32)"
  export AGENT_PROPOSAL_SIGNING_KEY
fi

backend_pid=""
frontend_pid=""

cleanup() {
  trap - INT TERM EXIT

  for pid in "$backend_pid" "$frontend_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done

  wait 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "Starting backend: http://127.0.0.1:8000"
(
  cd "$BACKEND_DIR" || exit 1
  exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) &
backend_pid=$!

echo "Starting frontend: http://127.0.0.1:5173"
(
  cd "$FRONTEND_DIR" || exit 1
  exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
) &
frontend_pid=$!

echo "Backend and frontend started. Press Ctrl+C to stop both."

# If either service exits, the EXIT trap stops the other one.
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

if ! kill -0 "$backend_pid" 2>/dev/null; then
  wait "$backend_pid"
  status=$?
  echo "Backend exited with status ${status}." >&2
else
  wait "$frontend_pid"
  status=$?
  echo "Frontend exited with status ${status}." >&2
fi

exit "$status"
