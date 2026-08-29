#!/usr/bin/env python3
"""F05 CAMOUFLAGE — préparation plateforme après F03_PICTOR.

Réencode le rendu PICTOR en H.264 yuv420p avec faststart, supprime les
métadonnées et gère aussi les vidéos sans piste audio.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SUSPICIOUS = ("remotion", "manim", "lavf", "lavc", "libav", "python", "claude")


def probe(path: Path) -> dict:
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1000:])
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    tags = {}
    tags.update(data.get("format", {}).get("tags", {}))
    for stream in data.get("streams", []):
        tags.update(stream.get("tags", {}))
    return {
        "duration_seconds": float(data.get("format", {}).get("duration", 0) or 0),
        "size_bytes": path.stat().st_size,
        "format": data.get("format", {}).get("format_name", "unknown"),
        "video_codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("r_frame_rate"),
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "tags": tags,
    }


def suspicious(tags: dict) -> list[str]:
    return [f"{key}={value}" for key, value in tags.items() if any(token in f"{key} {value}".lower() for token in SUSPICIOUS)]


def camouflage(source: Path, destination: Path, has_audio: bool) -> None:
    cmd = ["ffmpeg", "-y", "-i", str(source), "-map", "0:v:0", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p"]
    if has_audio:
        cmd += ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
    cmd += ["-map_metadata", "-1", "-metadata", "encoder=", "-movflags", "+faststart", str(destination)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])


def main() -> int:
    parser = argparse.ArgumentParser(description="F05 CAMOUFLAGE dev4")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.input.is_file():
        print(f"F05 input missing: {args.input}", file=sys.stderr)
        return 1
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "short_camouflaged.mp4"
    before = probe(args.input)
    camouflage(args.input, destination, before["has_audio"])
    after = probe(destination)
    residual_non_encoder = [tag for tag in suspicious(after["tags"]) if not tag.lower().startswith("encoder=")]
    report = {
        "schema_version": "dev4.camouflage.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "output": str(destination),
        "audio_policy": "preserve and loudnorm external audio" if before["has_audio"] else "video-only; no audio created",
        "before": {k: v for k, v in before.items() if k != "tags"},
        "after": {k: v for k, v in after.items() if k != "tags"},
        "suspicious_tags_before": suspicious(before["tags"]),
        "suspicious_tags_after": suspicious(after["tags"]),
        "metadata_residual_for_f06": suspicious(after["tags"]),
        "qa_pass": bool(after["video_codec"] == "h264" and after["width"] and after["height"] and not residual_non_encoder),
    }
    (args.output / "camouflage_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["qa_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
