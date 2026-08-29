#!/usr/bin/env python3
"""F06 LUTHER — nettoyage final sans réencodage."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

SUSPICIOUS = ("remotion", "manim", "lavf", "lavc", "libav", "python", "claude", "encoder")


def probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1000:])
    data = json.loads(result.stdout)
    tags = {}
    tags.update(data.get("format", {}).get("tags", {}))
    for stream in data.get("streams", []):
        tags.update(stream.get("tags", {}))
    return {"duration_seconds": float(data.get("format", {}).get("duration", 0) or 0), "size_bytes": path.stat().st_size, "format": data.get("format", {}).get("format_name"), "tags": tags, "streams": [{"type": s.get("codec_type"), "codec": s.get("codec_name"), "width": s.get("width"), "height": s.get("height")} for s in data.get("streams", [])]}


def strip_metadata(source: Path, destination: Path) -> None:
    result = subprocess.run(["ffmpeg", "-y", "-i", str(source), "-map", "0", "-c", "copy", "-map_metadata", "-1", "-fflags", "+bitexact", str(destination)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])


def main() -> int:
    parser = argparse.ArgumentParser(description="F06 LUTHER dev4")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    if not args.input.is_file():
        print(f"F06 input missing: {args.input}", file=sys.stderr)
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "short_master.mp4"
    before = probe(args.input)
    strip_metadata(args.input, destination)
    try:
        dt = datetime.strptime(args.date, "%Y-%m-%d").replace(hour=12)
        os.utime(destination, (dt.timestamp(), dt.timestamp()))
    except ValueError as exc:
        print(f"invalid date: {exc}", file=sys.stderr)
        return 1
    after = probe(destination)
    residual = [f"{k}={v}" for k, v in after["tags"].items() if any(token in f"{k} {v}".lower() for token in SUSPICIOUS)]
    report = {"schema_version": "dev4.luther.v1", "created_at": datetime.now(timezone.utc).isoformat(), "input": str(args.input), "output": str(destination), "before": before, "after": after, "suspicious_tags_after": residual, "stream_copy": True, "qa_pass": not residual and bool(after["streams"])}
    (args.output / "luther_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["qa_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
