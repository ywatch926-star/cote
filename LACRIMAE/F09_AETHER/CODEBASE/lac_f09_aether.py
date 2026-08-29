#!/usr/bin/env python3
"""F09 AETHER COMPOSITUM — Compositing multicouche par FFmpeg.

Reproduit la logique After Effects (cc2.ffx) en appliquant des couches
de filtres séquentielles : netteté, courbes, colorbalance, grain, etc.
Chaque preset est une configuration JSON versionnée avec opacité par couche.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRESETS_DIR = Path(__file__).resolve().parent.parent / "PRESETS"
PRESETS_FILE = PRESETS_DIR / "compositing_presets.json"

SUSPICIOUS = ("remotion", "manim", "lavf", "lavc", "libav", "python", "claude", "encoder")


def load_presets() -> dict:
    if not PRESETS_FILE.is_file():
        raise FileNotFoundError(f"presets introuvables: {PRESETS_FILE}")
    return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))


def get_preset(name: str) -> dict:
    data = load_presets()
    presets = data.get("presets", {})
    if name not in presets:
        available = ", ".join(presets.keys())
        raise ValueError(f"preset '{name}' introuvable. Disponibles: {available}")
    return presets[name]


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-1000:])
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", [])
                  if s.get("codec_type") == "video"), {})
    audio = next((s for s in data.get("streams", [])
                  if s.get("codec_type") == "audio"), None)
    tags = {}
    tags.update(data.get("format", {}).get("tags", {}))
    for stream in data.get("streams", []):
        tags.update(stream.get("tags", {}))
    return {
        "duration_seconds": float(data.get("format", {}).get("duration", 0) or 0),
        "size_bytes": path.stat().st_size,
        "format": data.get("format", {}).get("format_name"),
        "video_codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("r_frame_rate"),
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "tags": tags,
        "streams": [
            {"type": s.get("codec_type"), "codec": s.get("codec_name"),
             "width": s.get("width"), "height": s.get("height")}
            for s in data.get("streams", [])
        ],
    }


def build_filter_chain(preset: dict) -> str:
    """Construit la chaîne de filtres FFmpeg à partir des couches activées."""
    layers = [l for l in preset.get("layers", []) if l.get("enabled", True)]
    if not layers:
        raise ValueError("aucune couche activée dans le preset")

    filters = []
    for layer in layers:
        ffmpeg_filter = layer["ffmpeg_filter"]
        opacity = layer.get("opacity", 1.0)

        # Pour le grain, on l'applique directement (le opacity est contrôlé par c0s)
        if "noise=" in ffmpeg_filter:
            filters.append(ffmpeg_filter)
            continue

        # Pour les filtres eq/curves/colorbalance, on applique directement
        # L'opacité est interprétée comme un modulateur de l'intensité
        if opacity < 1.0:
            # On intensity-modulate les paramètres numériques
            modulated = _modulate_filter(ffmpeg_filter, opacity)
            filters.append(modulated)
        else:
            filters.append(ffmpeg_filter)

    chain = ",".join(filters)
    return chain


def _modulate_filter(filter_str: str, opacity: float) -> str:
    """Module l'intensité d'un filtre FFmpeg par un facteur d'opacité.

    Pour les filtres eq et colorbalance, on interpole entre l'identity (pas d'effet)
    et la valeur complète selon l'opacité.
    """
    import re

    if filter_str.startswith("eq="):
        return _modulate_eq(filter_str, opacity)
    elif filter_str.startswith("colorbalance="):
        return _modulate_colorbalance(filter_str, opacity)
    elif filter_str.startswith("curves="):
        # Les courbes sont déjà douces par conception, on garde tel quel
        return filter_str
    else:
        return filter_str


def _modulate_eq(filter_str: str, opacity: float) -> str:
    """Module les paramètres d'un filtre eq par opacité."""
    import re

    params_str = filter_str[3:]  # remove "eq="
    result_parts = []

    for part in params_str.split(":"):
        if "=" in part:
            key, val_str = part.split("=", 1)
            try:
                val = float(val_str)
                # Interpolation entre identity (0 pour brightness, 1 pour contrast/saturation/gamma)
                if key == "brightness":
                    modulated = val * opacity
                elif key in ("contrast", "saturation", "gamma"):
                    modulated = 1.0 + (val - 1.0) * opacity
                else:
                    modulated = val
                result_parts.append(f"{key}={modulated:.6f}")
            except ValueError:
                result_parts.append(part)
        else:
            result_parts.append(part)

    return "eq=" + ":".join(result_parts)


def _modulate_colorbalance(filter_str: str, opacity: float) -> str:
    """Module les paramètres d'un filtre colorbalance par opacité."""
    params_str = filter_str[13:]  # remove "colorbalance="
    result_parts = []

    for part in params_str.split(":"):
        if "=" in part:
            key, val_str = part.split("=", 1)
            try:
                val = float(val_str)
                modulated = val * opacity
                result_parts.append(f"{key}={modulated:.6f}")
            except ValueError:
                result_parts.append(part)
        else:
            result_parts.append(part)

    return "colorbalance=" + ":".join(result_parts)


def apply_compositing(source: Path, destination: Path, preset_name: str) -> dict:
    """Applique le preset de compositing multicouche à la vidéo source."""
    preset = get_preset(preset_name)
    global_cfg = preset.get("global", {})

    before = probe(source)
    if not before.get("video_codec"):
        raise ValueError("pas de flux vidéo dans la source")

    has_audio = before.get("has_audio", False)

    # Construire la chaîne de filtres
    filter_chain = build_filter_chain(preset)

    # Encoder settings
    codec = global_cfg.get("output_codec", "libx264")
    enc_preset = global_cfg.get("preset", "slow")
    crf = global_cfg.get("crf", 18)
    pix_fmt = global_cfg.get("pix_fmt", "yuv420p")
    movflags = global_cfg.get("movflags", "+faststart")

    tmp = destination.with_suffix(destination.suffix + ".aether.tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(source),
        "-vf", filter_chain,
        "-map", "0:v:0",
    ]

    if has_audio:
        command += ["-map", "0:a:0?"]
        command += ["-c:a", "copy"]
    else:
        command += ["-an"]

    command += [
        "-c:v", codec,
        "-preset", enc_preset,
        "-crf", str(crf),
        "-pix_fmt", pix_fmt,
        "-movflags", movflags,
        str(tmp),
    ]

    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(
            f"FFmpeg F09 a échoué:\n{result.stderr[-2000:]}"
        )
    elapsed = time.monotonic() - started

    # Remplacer le fichier de sortie
    tmp.replace(destination)

    after = probe(destination)

    # Vérifier les tags suspects
    residual_tags = [
        f"{k}={v}" for k, v in after["tags"].items()
        if any(token in f"{k} {v}".lower() for token in SUSPICIOUS)
        and not f"{k}".lower().startswith("encoder")
    ]

    # Rapport par couche
    layer_reports = []
    for layer in preset.get("layers", []):
        layer_reports.append({
            "id": layer["id"],
            "effect": layer.get("effect", "unknown"),
            "enabled": layer.get("enabled", True),
            "opacity": layer.get("opacity", 1.0),
            "ffmpeg_filter": layer["ffmpeg_filter"],
        })

    report = {
        "status": "SUCCEEDED",
        "stage": "F09_AETHER_COMPOSITUM",
        "preset": preset_name,
        "preset_description": preset.get("description", ""),
        "layers_applied": layer_reports,
        "filter_chain": filter_chain,
        "input": {
            "path": str(source.resolve()),
            "before": before,
        },
        "output": {
            "path": str(destination.resolve()),
            "after": after,
        },
        "encoding": {
            "codec": codec,
            "preset": enc_preset,
            "crf": crf,
            "pix_fmt": pix_fmt,
        },
        "elapsed_seconds": round(elapsed, 3),
        "suspicious_tags": residual_tags,
        "qa_pass": (
            after.get("video_codec") is not None
            and after.get("width") is not None
            and after.get("height") is not None
            and not residual_tags
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Écrire le rapport
    report_path = destination.parent / "aether_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="F09 AETHER COMPOSITUM — compositing multicouche FFmpeg"
    )
    parser.add_argument("--input", type=Path,
                        help="Vidéo source à traiter")
    parser.add_argument("--output", type=Path,
                        help="Répertoire de sortie")
    parser.add_argument("--preset", default="clean_realistic",
                        help="Nom du preset de compositing (défaut: clean_realistic)")
    parser.add_argument("--list-presets", action="store_true",
                        help="Lister les presets disponibles")
    args = parser.parse_args()

    if args.list_presets:
        data = load_presets()
        for name, cfg in data.get("presets", {}).items():
            enabled = sum(1 for l in cfg.get("layers", [])
                         if l.get("enabled", True))
            total = len(cfg.get("layers", []))
            print(f"  {name}: {cfg.get('description', '')} ({enabled}/{total} couches)")
        return 0

    if not args.input:
        parser.error("--input est requis sauf avec --list-presets")
    if not args.output:
        parser.error("--output est requis sauf avec --list-presets")
    if not args.input.is_file():
        print(f"F09 input absente: {args.input}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f"aether_{args.preset}.mp4"

    try:
        report = apply_compositing(args.input, destination, args.preset)
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["qa_pass"] else 1
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"F09_AETHER_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
