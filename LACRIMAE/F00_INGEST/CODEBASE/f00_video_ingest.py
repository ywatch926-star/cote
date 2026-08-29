#!/usr/bin/env python3
"""F00 vidéo dev6 — manifeste technique indépendant du manifeste éditorial dev4."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_video(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate,duration:stream_tags=rotate",
        "-show_entries", "format=duration", "-of", "json", str(path)
    ]
    data = json.loads(subprocess.check_output(command, text=True))
    stream = data.get("streams", [{}])[0]
    raw_rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1"
    numerator, denominator = raw_rate.split("/")
    fps = float(numerator) / float(denominator or 1)
    duration = float(stream.get("duration") or data.get("format", {}).get("duration") or 0)
    rotation = int((stream.get("tags") or {}).get("rotate", 0) or 0) % 360
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": round(fps, 6),
        "duration_seconds": round(duration, 6),
        "rotation": rotation,
        "estimated_frames": round(duration * fps),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="F00 video ingest dev6")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit(f"source absente: {args.source}")
    args.out.mkdir(parents=True, exist_ok=True)
    metadata = inspect_video(args.source)
    source_hash = sha256(args.source)
    manifest = {
        "schema_version": "dev6.video-source.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {"uri": str(args.source.resolve()), "sha256": source_hash, **metadata},
        "normalization": {"rotation_to_apply": metadata["rotation"], "audio": "preserve"},
        "status": "READY_FOR_ANALYSIS",
    }
    manifest_path = args.out / "source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {"stage": "F00_INGEST", "status": "SUCCEEDED", "manifest": str(manifest_path), "source_sha256": source_hash, "metadata": metadata}
    (args.out / "stage_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
