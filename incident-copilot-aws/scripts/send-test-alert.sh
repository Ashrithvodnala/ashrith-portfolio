#!/usr/bin/env bash
# Sends a sample Alertmanager alert and waits for the AI incident report.
# Usage: ./scripts/send-test-alert.sh [url]     (default http://localhost:8000)
set -euo pipefail
URL="${1:-http://localhost:8000}"
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Sending test alert to $URL/investigate ..."
curl -sS -X POST "$URL/investigate" -H "Content-Type: application/json" --data @"$DIR/sample-alert.json" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["report"]); print("\ntools:", d["tools_used"], "| seconds:", d["seconds"], "| tokens:", d["tokens"])'
