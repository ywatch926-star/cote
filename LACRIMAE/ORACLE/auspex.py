"""AUSPEX PIXEL/TEMPORAL — analyse locale sans GPU pour LACRIMAE v2.

Le module mesure des propriétés observables de la source et ne traite pas la vidéo.
Il utilise FFmpeg et Pillow afin de rester exécutable dans un environnement CPU léger.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def _probe(path: Path) -> dict[str, Any]:
    raw = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=width,height,avg_frame_rate,nb_frames:format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    payload = json.loads(raw)
    stream = payload.get("streams", [{}])[0]
    rate = stream.get("avg_frame_rate", "0/0")
    n, d = (int(x) for x in rate.split("/", 1))
    return {"width": int(stream.get("width") or 0), "height": int(stream.get("height") or 0),
            "fps": round(n / d, 6) if d else 0.0,
            "frames": int(stream.get("nb_frames") or 0),
            "duration_seconds": float(payload.get("format", {}).get("duration") or 0.0)}


def _read_frame(path: Path, index: int, total: int, duration: float) -> Image.Image | None:
    timestamp = (index / max(total - 1, 1)) * max(duration, 0.0)
    timestamp = min(timestamp, max(duration - 0.20, 0.0))
    target = Path("/tmp") / f"lacrimae_auspex_{path.stem}_{index}.jpg"
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{timestamp:.6f}",
                        "-i", str(path), "-frames:v", "1", "-q:v", "2", str(target)], check=True)
        if not target.is_file():
            return None
        return Image.open(target).convert("RGB")
    finally:
        target.unlink(missing_ok=True)


def _frame_stats(image: Image.Image) -> tuple[float, float, float, float, float, float]:
    rgb = np.asarray(image, dtype=np.float32) / 255.0
    gray = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    chroma_max = rgb.max(axis=2)
    chroma_min = rgb.min(axis=2)
    saturation = np.where(chroma_max > 0, (chroma_max - chroma_min) / np.maximum(chroma_max, 1e-6), 0.0)
    dx = np.diff(gray, axis=1, prepend=gray[:, :1])
    dy = np.diff(gray, axis=0, prepend=gray[:1, :])
    gradient = np.sqrt(dx * dx + dy * dy)
    sharpness = float(np.var(dx[:, 1:] - dx[:, :-1]) + np.var(dy[1:, :] - dy[:-1, :]))
    edge_density = float((gradient > 0.12).mean())
    return (float(gray.mean()), float(gray.std()), float(saturation.mean()),
            float((gray <= 0.025).mean()), float((gray >= 0.975).mean()), sharpness, edge_density)


def analyze_video(path: Path, sample_count: int = 24) -> dict[str, Any]:
    metadata = _probe(path)
    total = metadata["frames"]
    if total <= 0:
        raise ValueError("AUSPEX ne peut pas lire le nombre d’images")
    indices = np.linspace(0, max(total - 1, 0), min(sample_count, total), dtype=int)
    luma_means: list[float] = []
    luma_stds: list[float] = []
    saturations: list[float] = []
    black_clip: list[float] = []
    white_clip: list[float] = []
    sharpness: list[float] = []
    edges: list[float] = []
    motion: list[float] = []
    previous = None
    for index in indices:
        image = _read_frame(path, int(index), total, metadata["duration_seconds"])
        if image is None:
            continue
        stats = _frame_stats(image)
        luma, contrast, saturation, black, white, sharp, edge = stats
        luma_means.append(luma); luma_stds.append(contrast); saturations.append(saturation)
        black_clip.append(black); white_clip.append(white); sharpness.append(sharp); edges.append(edge)
        gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
        if previous is not None:
            motion.append(float(np.abs(gray - previous).mean()))
        previous = gray
    if not luma_means:
        raise ValueError("AUSPEX n’a extrait aucune frame")
    mean_motion = float(np.mean(motion)) if motion else 0.0
    contrast = float(np.mean(luma_stds)); saturation = float(np.mean(saturations))
    black_ratio = float(np.mean(black_clip)); white_ratio = float(np.mean(white_clip))
    if black_ratio > 0.12 and contrast > 0.22:
        profile = "realistic_aurea"
    elif contrast > 0.24 or saturation > 0.48:
        profile = "hdr_imperator"
    else:
        profile = "realistic_aurea"
    return {
        "implementation": "auspex_pixel_temporal_cpu_v2_pillow",
        "metadata": metadata,
        "samples": len(luma_means),
        "pixel": {"luma_mean": round(float(np.mean(luma_means)), 6),
                  "luma_std": round(contrast, 6), "saturation_mean": round(saturation, 6),
                  "black_clip_ratio": round(black_ratio, 6), "white_clip_ratio": round(white_ratio, 6),
                  "sharpness_gradient": round(float(np.mean(sharpness)), 6),
                  "edge_density": round(float(np.mean(edges)), 6)},
        "temporal": {"motion_mean": round(mean_motion, 6),
                     "motion_peak": round(float(max(motion) if motion else 0.0), 6),
                     "sampled_frame_indices": [int(x) for x in indices]},
        "recommendation": {"profile": profile,
                           "motus_mode": "viral" if mean_motion >= 0.12 else "cinematic",
                           "reason": "profil choisi à partir de luminance, contraste, saturation et mouvement"},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AUSPEX PIXEL/TEMPORAL sans GPU")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--samples", type=int, default=24)
    args = parser.parse_args()
    result = analyze_video(args.source, max(4, args.samples))
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
