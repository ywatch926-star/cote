#!/usr/bin/env python3
"""Exécuteur commun de frégate dev6.

Le mode `contract` valide le transit sans calcul lourd. Le mode `copy` sert
aux frégates légères et aux tests de chaîne. Les moteurs IA GPU remplaceront
le traitement interne sans changer le contrat de rapport.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="dev6 common frigate runner")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mode", choices=["contract", "copy"], default="contract")
    args = parser.parse_args()
    started = time.monotonic()
    if not args.input.is_file():
        raise SystemExit(f"input absente: {args.input}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    input_hash = sha256(args.input)
    if args.mode == "copy":
        shutil.copy2(args.input, args.output)
        output_hash = sha256(args.output)
    else:
        output_hash = None
    report = {
        "stage": args.stage,
        "status": "SUCCEEDED",
        "mode": args.mode,
        "input_path": str(args.input.resolve()),
        "input_sha256": input_hash,
        "output_path": str(args.output.resolve()),
        "output_sha256": output_hash,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "warnings": ["contract_only_no_ai_processing"] if args.mode == "contract" else [],
    }
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
