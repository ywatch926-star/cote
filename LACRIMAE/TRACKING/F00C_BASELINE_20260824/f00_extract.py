#!/usr/bin/env python3
"""F00-B EXTRACTOR — matérialise et valide les séquences du plan F00-A."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def probe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_frames,nb_read_frames,duration",
        "-of", "json", str(path),
    ]
    stream = json.loads(subprocess.check_output(cmd, text=True))["streams"][0]
    stream["nb_frames"] = stream.get("nb_read_frames") or stream.get("nb_frames") or 0
    return stream


def luma_stats(path: Path) -> dict:
    width, height = 32, 18
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={width}:{height},format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    raw = subprocess.check_output(cmd)
    size = width * height
    if not raw:
        return {"mean": 0.0, "max": 0.0, "frames": 0}
    values = np.frombuffer(raw, dtype=np.uint8)
    frame_means = values[: len(values) - len(values) % size].reshape(-1, size).mean(axis=1) / 255.0
    return {"mean": float(frame_means.mean()), "max": float(frame_means.max()), "frames": int(len(frame_means))}


def main() -> int:
    parser = argparse.ArgumentParser(description="F00-B Extractor")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-luma", type=float, default=0.03)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    source = args.source.resolve()
    sequence_dir = args.out / "sequences"
    sequence_dir.mkdir(parents=True, exist_ok=True)
    fps = float(plan["fps"])
    extracted, rejected = [], []
    for row in plan["sequences"]:
        sequence_id = row["id"]
        duration = int(row.get("timeline_duration_frames") or row.get("duration_frames") or plan["cut_interval_frames"])
        source_start = int(row["source_start_frame"])
        output = sequence_dir / f"{sequence_id}.mp4"
        start_seconds = source_start / fps
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start_seconds:.6f}", "-i", str(source),
            "-frames:v", str(duration), "-an", "-c:v", "libx264", "-profile:v", "main",
            "-pix_fmt", "yuv420p", "-r", f"{fps:.6f}", "-movflags", "+faststart", str(output),
        ]
        subprocess.run(cmd, check=True)
        stream = probe(output)
        stats = luma_stats(output)
        frame_count = int(stream.get("nb_frames") or 0)
        valid = output.stat().st_size > 0 and stream.get("codec_name") == "h264" and frame_count >= max(1, duration - 1) and stats["max"] >= args.min_luma
        record = dict(row)
        record.update({
            "file": f"sequences/{output.name}", "validated": bool(valid),
            "validation": {
                "codec": stream.get("codec_name"), "width": stream.get("width"), "height": stream.get("height"),
                "fps": stream.get("avg_frame_rate"), "frame_count": frame_count,
                "luma_mean_over_clip": round(stats["mean"], 6), "luma_max_over_clip": round(stats["max"], 6),
                "file_bytes": output.stat().st_size,
            },
        })
        if valid:
            extracted.append(record)
        else:
            rejected.append(record)
            output.unlink(missing_ok=True)
    if rejected:
        (args.out / "rejected_sequences.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(f"F00-B a rejeté {len(rejected)} séquences; consulter rejected_sequences.json")
    manifest = {
        "schema_version": "dev4.materialized-sequences.v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "project_title": plan.get("project_title"), "source": plan.get("source"), "source_metadata": plan.get("source_metadata"),
        "target_duration_seconds": plan["target_duration_seconds"], "fps": fps, "total_frames": plan["total_frames"],
        "cut_interval_frames": plan["cut_interval_frames"], "selection_mode": "f00a_luma_ranked_materialized", "materialized": True,
        "sequences": extracted, "validation": {"all_sequences_valid": True, "rejected_count": 0, "validated_at": datetime.now(timezone.utc).isoformat()},
    }
    args.out.mkdir(parents=True, exist_ok=True)
    destination = args.out / "sequences.json"
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"status": "ok", "stage": "F00-B_EXTRACT", "sequence_count": len(extracted), "rejected_count": 0, "manifest": str(destination), "directory": str(sequence_dir)}
    (args.out / "extract_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
