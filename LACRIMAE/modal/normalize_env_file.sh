#!/usr/bin/env bash
set -euo pipefail
file="${1:-.env.modal}"
tmp="${file}.tmp"
awk '
  /^MODAL_TOKEN_ID=/ {
    sub(/^[^=]*=[[:space:]]*/, "", $0)
    gsub(/[\r[:space:]]+$/, "", $0)
    if ($0 ~ /^".*"$/) { sub(/^"/, "", $0); sub(/"$/, "", $0) }
    print "MODAL_TOKEN_ID=" $0
    next
  }
  /^MODAL_TOKEN_SECRET=/ {
    sub(/^[^=]*=[[:space:]]*/, "", $0)
    gsub(/[\r[:space:]]+$/, "", $0)
    if ($0 ~ /^".*"$/) { sub(/^"/, "", $0); sub(/"$/, "", $0) }
    print "MODAL_TOKEN_SECRET=" $0
    next
  }
  { print }
' "$file" > "$tmp"
chmod 600 "$tmp"
mv -f "$tmp" "$file"
