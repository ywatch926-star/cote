#!/usr/bin/env python3
"""Télécharge un artifact GitHub appartenant à un run précis."""
from __future__ import annotations
import io
import os
import sys
import time
import zipfile
from pathlib import Path
import requests

OWNER_REPO = "kioka8877-ux/LACRIMAE"
API = "https://api.github.com"


def get_json(url: str, headers: dict) -> dict:
    for attempt in range(5):
        r = requests.get(url, headers=headers, timeout=90)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"GitHub API indisponible: {url}")


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: download_artifact_run.py RUN_ID ARTIFACT_NAME OUTPUT_DIR")
    run_id, artifact_name, output_dir = sys.argv[1:]
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN/GITHUB_TOKEN manquant")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = get_json(f"{API}/repos/{OWNER_REPO}/actions/runs/{run_id}/artifacts", headers)
    matches = [a for a in data.get("artifacts", []) if a["name"] == artifact_name and not a.get("expired")]
    if len(matches) != 1:
        names = [a["name"] for a in data.get("artifacts", [])]
        raise SystemExit(f"Artifact {artifact_name!r} absent ou ambigu dans run {run_id}; disponibles={names}")
    artifact = matches[0]
    for attempt in range(5):
        r = requests.get(artifact["archive_download_url"], headers=headers, timeout=180, allow_redirects=True)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        try:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            z.extractall(out)
            print(f"Downloaded {artifact_name} from run {run_id} -> {out}")
            return
        except zipfile.BadZipFile:
            time.sleep(2 ** attempt)
    raise SystemExit(f"Téléchargement artifact impossible: {artifact_name}")


if __name__ == "__main__":
    main()
