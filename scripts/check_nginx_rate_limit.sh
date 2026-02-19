#!/usr/bin/env bash
set -euo pipefail

URL="${1:-https://cannamente.com/}"
TOTAL="${2:-50}"
CONCURRENCY="${3:-10}"
RESOLVE_IP="${4:-}"

CURL_ARGS=(-s -o /dev/null -w "%{http_code}\n" --max-time 10)

if [[ -n "$RESOLVE_IP" ]]; then
  host="$(echo "$URL" | sed -E 's#https?://([^/:]+).*#\1#')"
  port="$(echo "$URL" | sed -E 's#https?://[^/:]+:([0-9]+).*#\1#')"
  if [[ "$URL" == https://* ]]; then
    scheme="https"
  else
    scheme="http"
  fi
  if [[ -z "$port" ]]; then
    if [[ "$scheme" == "https" ]]; then
      port="443"
    else
      port="80"
    fi
  fi
  CURL_ARGS+=(--resolve "${host}:${port}:${RESOLVE_IP}")
fi

echo "Target: $URL"
echo "Requests: $TOTAL, Concurrency: $CONCURRENCY"
if [[ -n "$RESOLVE_IP" ]]; then
  echo "Resolve: $RESOLVE_IP"
fi

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

seq "$TOTAL" | xargs -P "$CONCURRENCY" -I{} curl "${CURL_ARGS[@]}" "$URL" > "$tmp_file"

echo "Status code distribution:"
sort "$tmp_file" | uniq -c | sort -nr

if grep -Eq '^(429|503)$' "$tmp_file"; then
  echo "Rate limiting observed (429/503)."
else
  echo "Rate limiting NOT observed."
fi
