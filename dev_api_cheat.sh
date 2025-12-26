#!/usr/bin/env bash
set -euo pipefail

# Simple dev helper for 42's API

# Default to the local server if BASE isn't set
BASE="${BASE:-http://0.0.0.0:8000}"

# Prefer KEY, fall back to SAFE_KEY
KEY="${KEY:-${SAFE_KEY:-}}"

if [[ -z "${KEY:-}" ]]; then
  echo "ERROR: KEY or SAFE_KEY not set."
  echo "Try:  export KEY=\"\$SAFE_KEY\""
  exit 1
fi

case "${1:-}" in
  version)
    echo ">>> GET $BASE/version"
    curl -i -H "SAFE-KEY: $KEY" "$BASE/version"
    ;;
  chat)
    shift || true
    INPUT="${*:-Hello from dev_api_cheat.sh}"
    echo ">>> POST $BASE/chat  ::  $INPUT"
    curl -i \
      -H "SAFE-KEY: $KEY" \
      -H "Content-Type: application/json" \
      -d "{\"input\":\"$INPUT\"}" \
      "$BASE/chat"
    ;;
  *)
    echo "Usage:"
    echo "  ./dev_api_cheat.sh version"
    echo "  ./dev_api_cheat.sh chat \"your message here\""
    ;;
esac