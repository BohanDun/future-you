#!/usr/bin/env bash

set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

missing=()

require_value() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    missing+=("$name")
  fi
}

require_frontend_value() {
  local name="$1"
  if [[ -n "${!name:-}" ]]; then
    return
  fi
  if [[ -f "$PROJECT_DIR/frontend/.env.local" ]] &&
    grep -Eq "^${name}=.+$" "$PROJECT_DIR/frontend/.env.local"; then
    return
  fi
  missing+=("$name (shell or frontend/.env.local)")
}

require_value COGNITO_USER_POOL_ID
require_value COGNITO_APP_CLIENT_ID
require_frontend_value VITE_COGNITO_USER_POOL_ID
require_frontend_value VITE_COGNITO_USER_POOL_CLIENT_ID
require_value USER_PROFILE_TABLE_NAME
require_value BEDROCK_MODEL_ID
require_value AGENT_PROPOSAL_SIGNING_KEY

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "AWS mode is not configured. Missing environment variables:" >&2
  for name in "${missing[@]}"; do
    echo "  - $name" >&2
  done
  echo >&2
  echo "Follow: $PROJECT_DIR/docs/AWS_AUTH_SETUP.md" >&2
  echo "Then run this script again." >&2
  exit 2
fi

if [[ ${#AGENT_PROPOSAL_SIGNING_KEY} -lt 32 ]]; then
  echo "AWS mode is not configured: AGENT_PROPOSAL_SIGNING_KEY must contain at least 32 characters." >&2
  echo "Generate one with: openssl rand -hex 32" >&2
  exit 2
fi

export AUTH_MODE=cognito
export DATA_SOURCE=dynamodb
export AI_MODE=bedrock
export VITE_AUTH_MODE=cognito
export FUTURE_YOU_RUNTIME_PROFILE=aws

exec "$PROJECT_DIR/start-dev.sh"
