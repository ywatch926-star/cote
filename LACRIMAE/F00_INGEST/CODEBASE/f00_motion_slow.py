#!/usr/bin/env python3
"""F00-C MOTION SLOW — interpolation de mouvement optionnelle sur les sorties F00-B.

Le script ne modifie jamais les séquences normales. Il produit un manifeste parallèle
et des fichiers MP4 traités uniquement lorsque l'opérateur active F00-C.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def probe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_frames,nb_read_frames,duration",
        "-of", "json", str(path),
    ]
    data = json.loads(subprocess.check_output(cmd, text=True))
    stream = data["streams"][0]
    stream["nb_frames"] = stream.get("nb_read_frames") or stream.get("nb_frames") or 0
    return stream


def parse_ranges(value: str, fps: float, target_duration: float) -> list[tuple[float, float]]:
    if not value.strip():
        return []
    ranges = []
    for token in value.split(","):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[-:]\s*(\d+(?:\.\d+)?)\s*", token)
        if not match:
            raise ValueError(f"Plage invalide: {token!r}. Format attendu: debut-fin")
        start, end = float(match.group(1)), float(match.group(2))
        if start < 0 or end <= start or end > target_duration:
            raise ValueError(f"Plage hors limites: {start}-{end}s pour une cible de {target_duration}s")
        ranges.append((start, end))
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:]):
        if current[0] < previous[1]:
            raise ValueError("Les plages Motion Slow se chevauchent")
    return ranges


def in_requested_range(row: dict, ranges: list[tuple[float, float]], fps: float) -> bool:
    start = float(row.get("timeline_start_frame", 0)) / fps
    duration = float(row.get("duration_frames") or row.get("timeline_duration_frames") or 0) / fps
    end = start + duration
    return any(start < requested_end and end > requested_start for requested_start, requested_end in ranges)


def main() -> int:
    parser = argparse.ArgumentParser(description="F00-C Motion Slow")
    parser.add_argument("--source", type=Path, required=True, help="Source vidéo, conservée comme référence")
    parser.add_argument("--manifest", type=Path, required=True, help="sequences.json produit par F00-B")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=["off", "partial", "global"], default="off")
    parser.add_argument("--speed", type=float, default=0.5, help="Vitesse slow motion, entre 0.25 et 0.75")
    parser.add_argument("--ranges", default="", help="Plages secondes: 3-7,8-9")
    parser.add_argument("--engine", choices=["ffmpeg_minterpolate"], default="ffmpeg_minterpolate")
    args = parser.parse_args()

    if not 0.25 <= args.speed <= 0.75:
        raise ValueError("La vitesse doit être comprise entre 0.25 et 0.75")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fps = float(manifest["fps"])
    target_duration = float(manifest["target_duration_seconds"])
    ranges = parse_ranges(args.ranges, fps, target_duration)
    if args.mode == "partial" and not ranges:
        raise ValueError("Le mode partial exige --ranges, par exemple 3-7")
    if args.mode == "global":
        ranges = [(0.0, target_duration)]

    args.out.mkdir(parents=True, exist_ok=True)
    output_dir = args.out / "sequences"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_rows = []
    processed_count = 0

    for row in manifest["sequences"]:
        duration = int(row.get("timeline_duration_frames") or row.get("duration_frames") or manifest["cut_interval_frames"])
        input_path = args.manifest.parent / row["file"]
        if not input_path.exists():
            raise FileNotFoundError(f"Séquence F00-B introuvable: {input_path}")
        should_process = args.mode != "off" and in_requested_range(row, ranges, fps)
        output_name = f"{row['id']}_{'slow' if should_process else 'normal'}.mp4"
        output_path = output_dir / output_name
        if should_process:
            # On étire le temps puis minterpolate reconstruit les frames manquantes
            # à la cadence de sortie. Les cuts normaux restent inchangés.
            # Le ralenti génère davantage de frames, puis on recoupe à la durée
            # timeline d’origine pour conserver la durée cible du Short.
            clip_seconds = max(1.0 / fps, duration / fps)
            filter_graph = (
                f"setpts=PTS/{args.speed},"
                f"minterpolate=fps={fps:.6f}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
                f"trim=duration={clip_seconds:.9f},setpts=PTS-STARTPTS"
            )
            run([
                "ffmpeg", "-y", "-v", "error", "-i", str(input_path),
                "-vf", filter_graph, "-an", "-c:v", "libx264", "-profile:v", "main",
                "-pix_fmt", "yuv420p", "-r", f"{fps:.6f}", "-frames:v", str(duration), "-movflags", "+faststart", str(output_path),
            ])
            processed_count += 1
        else:
            shutil.copy2(input_path, output_path)

        stream = probe(output_path)
        new_row = dict(row)
        new_row.update({
            "file": f"sequences/{output_name}",
            "motion_slow": bool(should_process),
            "motion_slow_speed": args.speed if should_process else 1.0,
            "motion_slow_engine": args.engine if should_process else None,
            "duration_frames": int(stream.get("nb_frames") or row.get("duration_frames") or 0),
            "validation": {
                "codec": stream.get("codec_name"),
                "width": stream.get("width"),
                "height": stream.get("height"),
                "fps": stream.get("avg_frame_rate"),
                "frame_count": int(stream.get("nb_frames") or 0),
                "file_bytes": output_path.stat().st_size,
            },
        })
        output_rows.append(new_row)

    total_frames = sum(int(row.get("duration_frames") or 0) for row in output_rows)
    output_manifest = {
        "schema_version": "dev4.motion-slow-sequences.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_title": manifest.get("project_title"),
        "source": manifest.get("source"),
        "source_metadata": manifest.get("source_metadata"),
        "target_duration_seconds": total_frames / fps,
        "requested_target_duration_seconds": target_duration,
        "fps": fps,
        "total_frames": total_frames,
        "cut_interval_frames": manifest.get("cut_interval_frames"),
        "materialized": True,
        "motion_slow": {
            "enabled": args.mode != "off",
            "mode": args.mode,
            "speed": args.speed,
            "engine": args.engine,
            "ranges_seconds": [{"start": start, "end": end} for start, end in ranges],
            "processed_sequence_count": processed_count,
        },
        "sequences": output_rows,
        "validation": {
            "all_sequences_present": True,
            "processed_sequence_count": processed_count,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    destination = args.out / "motion_slow_manifest.json"
    destination.write_text(json.dumps(output_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "status": "ok",
        "stage": "F00-C_MOTION_SLOW",
        "mode": args.mode,
        "engine": args.engine,
        "speed": args.speed,
        "ranges_seconds": ranges,
        "processed_sequence_count": processed_count,
        "sequence_count": len(output_rows),
        "total_frames": total_frames,
        "duration_seconds": total_frames / fps,
        "manifest": str(destination),
    }
    (args.out / "motion_slow_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

