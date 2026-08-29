#!/usr/bin/env bash
set -euo pipefail

APP_FILE="modal/workers/video_worker.py"
VIDEO_VOLUME="${LACRIMAE_VIDEO_VOLUME:-lacrimae-dev6-video}"
MODEL_VOLUME="${LACRIMAE_MODEL_VOLUME:-lacrimae-dev6-models}"

command -v modal >/dev/null 2>&1 || {
  echo "ERREUR: installez le CLI Modal et authentifiez-vous avant ce script." >&2
  exit 1
}

modal volume create "$VIDEO_VOLUME" 2>/dev/null || true
modal volume create "$MODEL_VOLUME" 2>/dev/null || true
modal deploy "$APP_FILE"

echo "Volumes prêts : $VIDEO_VOLUME, $MODEL_VOLUME"
echo "Application déployée : $APP_FILE"
