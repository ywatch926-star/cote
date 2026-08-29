#!/usr/bin/env python3
"""F00-A SCOUT — identifie et classe des passages vidéo exploitables.

Le scout ne crée aucun clip. Il échantillonne la source avec FFmpeg, calcule une
luminosité et une variance simples, élimine les images quasi noires et produit
un plan que F00-B pourra matérialiser.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def probe_video(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,duration",
        "-of", "json", str(path),
    ]
    stream = json.loads(subprocess.check_output(cmd, text=True))["streams"][0]
    num, den = (stream.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    duration = float(stream.get("duration") or 0)
    frames = int(stream.get("nb_frames") or round(duration * fps))
    if fps <= 0 or duration <= 0 or frames <= 0:
        raise ValueError("Source vidéo sans FPS, durée ou frames valides")
    return {"width": int(stream.get("width") or 0), "height": int(stream.get("height") or 0), "fps": round(fps, 6), "duration_seconds": round(duration, 6), "total_frames": frames}


def sample_luminance(source: Path, meta: dict, sample_fps: float) -> list[dict]:
    width, height = 64, 36
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(source), "-vf",
        f"fps={sample_fps},scale={width}:{height},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    frame_bytes = width * height
    rows: list[dict] = []
    index = 0
    assert proc.stdout is not None
    while True:
        raw = proc.stdout.read(frame_bytes)
        if len(raw) != frame_bytes:
            break
        pixels = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        rows.append({
            "time_seconds": index / sample_fps,
            "mean_luma": round(float(pixels.mean()) / 255.0, 6),
            "luma_std": round(float(pixels.std()) / 255.0, 6),
        })
        index += 1
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"Échantillonnage FFmpeg échoué ({code})")
    return rows


def build_plan(source: Path, request: dict) -> dict:
    meta = probe_video(source)
    fps = float(request.get("fps") or meta["fps"])
    target = float(request.get("target_duration_seconds", 10))
    cut_frames = max(1, int(request.get("cut_interval_frames", 7)))
    total_output = max(1, round(target * fps))
    needed = math.ceil(total_output / cut_frames)
    sample_fps = float(request.get("scout_sample_fps", 2.0))
    min_luma = float(request.get("min_mean_luma", 0.075))
    min_std = float(request.get("min_luma_std", 0.025))
    min_gap = float(request.get("min_candidate_gap_seconds", 0.35))
    samples = sample_luminance(source, meta, sample_fps)
    eligible = [row for row in samples if row["mean_luma"] >= min_luma and row["luma_std"] >= min_std]
    eligible.sort(key=lambda row: (row["mean_luma"] + row["luma_std"] * 0.5), reverse=True)
    picked: list[dict] = []
    for row in eligible:
        if all(abs(row["time_seconds"] - other["time_seconds"]) >= min_gap for other in picked):
            picked.append(row)
        if len(picked) >= max(needed * 2, int(request.get("candidate_count", needed * 2))):
            break
    if not picked:
        raise RuntimeError("F00-A n'a trouvé aucun candidat visuellement exploitable")
    picked.sort(key=lambda row: row["time_seconds"])
    candidates = []
    for index, row in enumerate(picked, 1):
        start = min(meta["total_frames"] - cut_frames - 1, max(0, round(row["time_seconds"] * fps)))
        candidates.append({
            "id": f"candidate_{index:04d}",
            "source": source.name,
            "source_start_frame": start,
            "source_end_frame": min(start + cut_frames - 1, meta["total_frames"] - 1),
            "source_start_seconds": round(start / fps, 6),
            "duration_frames": cut_frames,
            "mean_luma": row["mean_luma"],
            "luma_std": row["luma_std"],
            "visibility_score": round(row["mean_luma"] + row["luma_std"] * 0.5, 6),
            "status": "scouted",
        })
    selected = []
    for index in range(needed):
        candidate = dict(candidates[index % len(candidates)])
        timeline_start = index * cut_frames
        timeline_end = min(total_output - 1, (index + 1) * cut_frames - 1)
        candidate.update({
            "id": f"seq_{index + 1:04d}",
            "timeline_start_frame": timeline_start,
            "timeline_end_frame": timeline_end,
            "timeline_duration_frames": timeline_end - timeline_start + 1,
        })
        selected.append(candidate)
    return {
        "schema_version": "dev4.sequence-plan.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_title": request.get("project_title", source.stem),
        "source": source.name,
        "source_metadata": meta,
        "target_duration_seconds": target,
        "fps": fps,
        "total_frames": total_output,
        "cut_interval_frames": cut_frames,
        "selection_policy": {"mode": "luma_ranked_scout", "min_mean_luma": min_luma, "min_luma_std": min_std, "sample_fps": sample_fps},
        "candidate_sequences": candidates,
        "sequences": selected,
        "materialization_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="F00-A Scout")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    plan = build_plan(args.source, request)
    destination = args.out / "sequences_plan.json"
    destination.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"status": "ok", "stage": "F00-A_SCOUT", "candidate_count": len(plan["candidate_sequences"]), "sequence_count": len(plan["sequences"]), "plan": str(destination)}
    (args.out / "scout_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
