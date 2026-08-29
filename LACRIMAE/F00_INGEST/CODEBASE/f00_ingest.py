#!/usr/bin/env python3
"""F00 INGEST — construit un manifeste de séquences virtuelles.

Aucune vidéo n'est découpée ni exportée : le manifeste référence des frames
et des timecodes dans la vidéo source pour F03_PREVIEW et F03_PICTOR.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def probe_video(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,duration",
        "-of", "json", str(path),
    ]
    raw = subprocess.check_output(cmd, text=True)
    stream = json.loads(raw)["streams"][0]
    rate_num, rate_den = (stream.get("avg_frame_rate") or "30/1").split("/")
    fps = float(rate_num) / float(rate_den or 1)
    duration = float(stream.get("duration") or 0)
    frames = int(stream.get("nb_frames") or round(duration * fps))
    if not frames or not duration:
        raise ValueError("Impossible de déterminer la durée ou le nombre de frames")
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": round(fps, 6),
        "duration_seconds": round(duration, 6),
        "total_frames": frames,
    }


def build_manifest(source: Path, request: dict, meta: dict) -> dict:
    fps = float(request.get("fps") or meta["fps"])
    target_seconds = float(request.get("target_duration_seconds", 10))
    cut_frames = max(1, int(request.get("cut_interval_frames", 7)))
    output_frames = max(1, round(target_seconds * fps))
    used_count = math.ceil(output_frames / cut_frames)
    candidate_count = max(used_count, int(request.get("candidate_count", used_count * 2)))
    rng = random.Random(int(request.get("shuffle_seed", 2026)))

    max_start = max(0, meta["total_frames"] - cut_frames - 1)
    if max_start == 0:
        starts = [0] * candidate_count
    else:
        starts = sorted({rng.randint(0, max_start) for _ in range(candidate_count * 4)})
        while len(starts) < candidate_count:
            starts.append(rng.randint(0, max_start))
        starts = starts[:candidate_count]
    rng.shuffle(starts)

    candidates = []
    for index, start in enumerate(starts, 1):
        end = min(start + cut_frames, meta["total_frames"] - 1)
        candidates.append({
            "id": f"seq_{index:04d}",
            "source": source.name,
            "source_start_frame": start,
            "source_end_frame": end,
            "source_start_seconds": round(start / fps, 6),
            "source_end_seconds": round(end / fps, 6),
            "duration_frames": end - start + 1,
            "muted": True,
        })

    selected = []
    for index in range(used_count):
        item = dict(candidates[index % len(candidates)])
        item["timeline_start_frame"] = index * cut_frames
        item["timeline_end_frame"] = min(output_frames - 1, (index + 1) * cut_frames - 1)
        item["timeline_duration_frames"] = item["timeline_end_frame"] - item["timeline_start_frame"] + 1
        selected.append(item)

    return {
        "schema_version": "dev4.virtual-sequences.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_title": request.get("project_title", source.stem),
        "source": source.name,
        "source_metadata": meta,
        "target_duration_seconds": target_seconds,
        "fps": fps,
        "total_frames": output_frames,
        "cut_interval_frames": cut_frames,
        "shuffle_seed": int(request.get("shuffle_seed", 2026)),
        "candidate_sequences": candidates,
        "sequences": selected,
        "audio_policy": "source video audio ignored; external voiceover is optional",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="F00 virtual sequence manifest generator")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    args = parser.parse_args()
    request = {}
    if args.request and args.request.exists():
        request = json.loads(args.request.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    meta = probe_video(args.source)
    manifest = build_manifest(args.source, request, meta)
    destination = args.out / "sequences.json"
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"status": "ok", "source": str(args.source), "manifest": str(destination), "virtual_only": True, "sequence_count": len(manifest["sequences"]), "intermediate_video_files": 0}
    (args.out / "ingest_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
