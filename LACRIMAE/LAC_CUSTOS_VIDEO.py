#!/usr/bin/env python3
"""Gardien des transits vidéo dev6.

Validation légère, sans dépendances externes. Les vérifications FFprobe
seront ajoutées dans le lot suivant ; cette version verrouille déjà les
contrats d'état, les rapports et les chemins de campagne.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

STAGES = [
    "F00_INGEST", "F01_ANALYSIS", "F02_MOTUS", "F03_RESTAURA",
    "F04_UPSCALE", "F05_LUMEN", "F06_AUDIO", "F07_CUSTOS_VIDEO",
    "F08_CAMOUFLAGE", "F09_LUTHER",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(root: Path, campaign_id: str, stage: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if stage not in STAGES:
        return False, [f"frégate inconnue: {stage}"]
    base = root / "campaigns" / campaign_id
    state_path = base / "campaign_state.json"
    report_path = base / stage / "stage_report.json"
    if not state_path.is_file():
        errors.append(f"état absent: {state_path}")
    if not report_path.is_file():
        errors.append(f"rapport absent: {report_path}")
    if errors:
        return False, errors
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"JSON invalide: {exc}"]
    if state.get("campaign_id") != campaign_id:
        errors.append("campaign_id incohérent dans l'état")
    if report.get("campaign_id") != campaign_id:
        errors.append("campaign_id incohérent dans le rapport")
    if report.get("stage") != stage:
        errors.append("stage incohérent dans le rapport")
    if report.get("status") != "SUCCEEDED":
        errors.append("la frégate n'est pas marquée SUCCEEDED")
    if stage not in state.get("completed_stages", []):
        errors.append("la frégate n'est pas déclarée terminée dans l'état")
    if report.get("output_path"):
        output = Path(report["output_path"])
        if not output.is_file():
            errors.append(f"sortie absente: {output}")
        elif report.get("output_sha256") and sha256_file(output) != report["output_sha256"]:
            errors.append("hash de sortie incohérent")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="LAC_CUSTOS_VIDEO")
    parser.add_argument("--root", default=".")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--stage", required=True, choices=STAGES)
    args = parser.parse_args()
    ok, errors = validate(Path(args.root), args.campaign_id, args.stage)
    if ok:
        print(f"CUSTOS_VIDEO: {args.stage} TRANSIT VALIDÉ")
        return 0
    for error in errors:
        print(f"CUSTOS_VIDEO: ERREUR — {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
