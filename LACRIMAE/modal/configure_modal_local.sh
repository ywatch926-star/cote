#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${1:-.env.modal}"

get_value() {
  local name="$1"
  awk -v key="$name" '
    $0 ~ "^" key "=" {
      sub("^[^=]*=", "", $0)
      print $0
      exit
    }
  ' "$ENV_FILE"
}

TOKEN_ID="$(get_value MODAL_TOKEN_ID)"
TOKEN_SECRET="$(get_value MODAL_TOKEN_SECRET)"

if [[ -z "$TOKEN_ID" || -z "$TOKEN_SECRET" ]]; then
  echo "ERREUR: les deux variables Modal doivent être remplies." >&2
  exit 1
fi

command -v modal >/dev/null 2>&1 || {
  echo "ERREUR: le CLI Modal n'est pas installé." >&2
  exit 1
}

modal token set --token-id "$TOKEN_ID" --token-secret "$TOKEN_SECRET" --profile dev6 >/dev/null
unset TOKEN_ID TOKEN_SECRET
printf '%s\n' "Profil Modal dev6 configuré sans afficher les secrets."
