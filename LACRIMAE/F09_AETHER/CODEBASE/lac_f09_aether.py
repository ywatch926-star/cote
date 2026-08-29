#!/usr/bin/env python3
"""F09 AETHER COMPOSITUM v2 — Compositing multicouche par FFmpeg.

Reproduit fidèlement la chaîne After Effects extraite des projets .aep
de la release CC :
  S_Sharpen (×3) → BCC Unsharp Mask (×3) → MB Looks (ACES→Rec.709) → S_Glow (×2)

v2: supporte les filtres complexes (split/blend) pour le glow/bloom,
et les filtres simples (unsharp/eq/curves/colorbalance) chaînés.
"""
from __future__ import annotations

import argparse
import json
import re
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


def _is_complex_filter(filter_str: str) -> bool:
    """Détecte si un filtre est un filtre complexe (split/blend) vs simple."""
    return "split[" in filter_str or "blend=" in filter_str


def _modulate_eq(filter_str: str, opacity: float) -> str:
    """Module les paramètres d'un filtre eq par opacité."""
    params_str = filter_str[3:]  # remove "eq="
    result_parts = []

    for part in params_str.split(":"):
        if "=" in part:
            key, val_str = part.split("=", 1)
            try:
                val = float(val_str)
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


def _modulate_filter(filter_str: str, opacity: float) -> str:
    """Module l'intensité d'un filtre FFmpeg par un facteur d'opacité."""
    if filter_str.startswith("eq="):
        return _modulate_eq(filter_str, opacity)
    elif filter_str.startswith("colorbalance="):
        return _modulate_colorbalance(filter_str, opacity)
    elif filter_str.startswith("curves="):
        return filter_str
    else:
        return filter_str


def build_filter_command(preset: dict) -> tuple[str | None, list[str]]:
    """Construit la chaîne de filtres. Retourne (filter_complex_str, [-vf chain])
    
    Si le preset contient des filtres complexes (split/blend pour le glow),
    on utilise -filter_complex. Sinon, on utilise -vf avec une chaîne simple.
    """
    layers = [l for l in preset.get("layers", []) if l.get("enabled", True)]
    if not layers:
        raise ValueError("aucune couche activée dans le preset")

    has_complex = any(_is_complex_filter(l["ffmpeg_filter"]) for l in layers)

    if has_complex:
        return (_build_filter_complex(layers), [])
    else:
        filters = []
        for layer in layers:
            ff = layer["ffmpeg_filter"]
            opacity = layer.get("opacity", 1.0)
            if opacity < 1.0 and not ff.startswith("noise="):
                ff = _modulate_filter(ff, opacity)
            filters.append(ff)
        return (None, [",".join(filters)])


def _build_filter_complex(layers: list) -> str:
    """Construit un filter_complex FFmpeg pour les filtres mixtes (simples + glow).
    
    Stratégie :
    - Les filtres simples (unsharp, eq, curves, colorbalance) sont chaînés via commas
    - Les filtres glow (split+blend) sont des sous-graphes séparés avec labels uniques
    - On les connecte en séquence avec des labels uniques par étape
    """
    simple_filters = []
    complex_filters = []
    
    for layer in layers:
        ff = layer["ffmpeg_filter"]
        opacity = layer.get("opacity", 1.0)
        
        if _is_complex_filter(ff):
            if opacity < 1.0:
                ff = ff.replace("all_opacity=0.", f"all_opacity={opacity:.2f}")
            complex_filters.append((layer["id"], ff))
        else:
            if opacity < 1.0 and not ff.startswith("noise="):
                ff = _modulate_filter(ff, opacity)
            simple_filters.append(ff)

    parts = []
    current_pad = "[0:v]"
    pad_idx = 0
    
    # D'abord, les filtres simples en chaîne
    if simple_filters:
        chain = ",".join(simple_filters)
        graded_label = f"[graded{pad_idx}]"
        parts.append(f"{current_pad}{chain}{graded_label}")
        current_pad = graded_label
        pad_idx += 1
    
    # Ensuite, les filtres glow (complex) — chacun avec labels uniques
    for glow_idx, (layer_id, ff) in enumerate(complex_filters):
        in_label = current_pad
        split_a = f"[gs{glow_idx}a]"
        split_b = f"[gs{glow_idx}b]"
        blurred_label = f"[gbl{glow_idx}]"
        glowbright_label = f"[ggb{glow_idx}]"
        
        # Extraire les paramètres du filtre original
        bb_match = re.search(r'boxblur=(\d+):(\d+)', ff)
        bb_size = bb_match.group(1) if bb_match else "20"
        curves_match = re.search(r"curves=m='([^']+)'", ff)
        curves_str = curves_match.group(1) if curves_match else "0/0 0.7/0.72 0.9/0.96 1/1"
        op_match = re.search(r'all_opacity=([\d.]+)', ff)
        opacity_val = op_match.group(1) if op_match else "0.35"
        
        is_last = (glow_idx == len(complex_filters) - 1)
        if is_last:
            out_label = ""
        else:
            out_label = f"[gg{glow_idx}]"
        
        glow_graph = (
            f"{in_label}split{split_a}{split_b};"
            f"{split_b}boxblur={bb_size}:{bb_size}{blurred_label};"
            f"{blurred_label}curves=m='{curves_str}'{glowbright_label};"
            f"{split_a}{glowbright_label}blend=all_mode=screen:all_opacity={opacity_val}{out_label}"
        )
        
        parts.append(glow_graph)
        current_pad = out_label if out_label else split_a
    
    return ";".join(parts)


def apply_compositing(source: Path, destination: Path, preset_name: str) -> dict:
    """Applique le preset de compositing multicouche à la vidéo source."""
    preset = get_preset(preset_name)
    global_cfg = preset.get("global", {})

    before = probe(source)
    if not before.get("video_codec"):
        raise ValueError("pas de flux vidéo dans la source")

    has_audio = before.get("has_audio", False)

    filter_complex, vf_chain = build_filter_command(preset)
    
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
        "-map", "0:v:0",
    ]

    if filter_complex:
        command += ["-filter_complex", filter_complex]
    else:
        command += ["-vf", vf_chain[0]]

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
            f"FFmpeg F09 a échoué:\nCommande: {' '.join(command[:10])}...\n"
            f"Erreur: {result.stderr[-2000:]}"
        )
    elapsed = time.monotonic() - started

    tmp.replace(destination)

    after = probe(destination)

    residual_tags = [
        f"{k}={v}" for k, v in after["tags"].items()
        if any(token in f"{k} {v}".lower() for token in SUSPICIOUS)
        and not f"{k}".lower().startswith("encoder")
    ]

    layer_reports = []
    for layer in preset.get("layers", []):
        layer_reports.append({
            "id": layer["id"],
            "effect": layer.get("effect", "unknown"),
            "ae_effect": layer.get("ae_effect", "unknown"),
            "enabled": layer.get("enabled", True),
            "opacity": layer.get("opacity", 1.0),
            "ffmpeg_filter": layer["ffmpeg_filter"][:80] + ("..." if len(layer["ffmpeg_filter"]) > 80 else ""),
        })

    report = {
        "status": "SUCCEEDED",
        "stage": "F09_AETHER_COMPOSITUM",
        "preset": preset_name,
        "preset_description": preset.get("description", ""),
        "ae_source": preset.get("ae_source", "unknown"),
        "layers_applied": layer_reports,
        "filter_type": "filter_complex" if filter_complex else "vf_chain",
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

    report_path = destination.parent / "aether_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="F09 AETHER COMPOSITUM v2 — compositing multicouche FFmpeg (basé sur projets CC)"
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
        print(f"Schema: {data.get('schema_version', '?')}")
        print(f"AE projects analyzed: {', '.join(data.get('ae_project_analyzed', []))}")
        print()
        for name, cfg in data.get("presets", {}).items():
            enabled = sum(1 for l in cfg.get("layers", [])
                         if l.get("enabled", True))
            total = len(cfg.get("layers", []))
            ae = cfg.get("ae_source", "unknown")
            print(f"  {name}: {cfg.get('description', '')[:80]}")
            print(f"    Source: {ae} | Couches: {enabled}/{total}")
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
