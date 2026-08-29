#!/usr/bin/env python3
"""Validate F00/preview/PICTOR contracts for dev4."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path}: {exc}") from exc


def validate_sequences(data: dict) -> None:
    schema = data.get("schema_version")
    if schema not in {"dev4.virtual-sequences.v1", "dev4.materialized-sequences.v1"}:
        raise ValueError("unsupported dev4 sequences schema_version")
    if schema == "dev4.materialized-sequences.v1" and data.get("materialized") is not True:
        raise ValueError("materialized manifest must set materialized=true")
    fps = float(data.get("fps", 0))
    total = int(data.get("total_frames", 0))
    interval = int(data.get("cut_interval_frames", 0))
    rows = data.get("sequences")
    if fps <= 0 or total <= 0 or interval <= 0 or not isinstance(rows, list) or not rows:
        raise ValueError("sequences manifest has invalid timing or empty sequences")
    previous_end = -1
    for row in rows:
        required = ("id", "source_start_frame", "timeline_start_frame", "timeline_duration_frames")
        if schema == "dev4.materialized-sequences.v1":
            required = required + ("file", "validated")
        if any(key not in row for key in required):
            raise ValueError(f"sequence missing required field: {row}")
        start = int(row["timeline_start_frame"])
        duration = int(row["timeline_duration_frames"])
        if start < 0 or duration <= 0 or start < previous_end:
            raise ValueError(f"sequence timeline is not monotonic: {row}")
        if schema == "dev4.materialized-sequences.v1" and row.get("validated") is not True:
            raise ValueError(f"materialized sequence is not validated: {row}")
        previous_end = start + duration
    if previous_end < total:
        raise ValueError(f"sequence timeline ends at {previous_end}, before total_frames {total}")


def validate_codex(data: dict) -> None:
    clips = data.get("clips")
    if not isinstance(clips, list) or not clips or not isinstance(clips[0], dict):
        raise ValueError("codex must contain at least one clip")
    video = clips[0].get("video") or {}
    if not video.get("source"):
        raise ValueError("codex clip video.source is required")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sequences", type=Path, required=True)
    parser.add_argument("--codex", type=Path)
    args = parser.parse_args()
    sequences = load(args.sequences)
    validate_sequences(sequences)
    if args.codex:
        validate_codex(load(args.codex))
    print(f"contracts ok: {len(sequences['sequences'])} timeline sequences, {sequences['total_frames']} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
