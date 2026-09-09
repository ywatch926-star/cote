#!/usr/bin/env python3
"""F00-PUR — Ingest segments VOD depuis les packs PUR de PERTURABO.

Le pack PUR ne contient PAS le fichier video : il contient vod_url +
start_sec + end_sec (ex: twitch.tv/videos/2864600351, 737.48 → 767.48).
Ce script telecharge UNIQUEMENT le segment via yt-dlp --download-sections
(doctrine F00B_VOX : jamais la VOD complete), valide les gates G0-G3,
et produit le manifeste pur_sources.json consomme par le workflow
dev10_pur_render.yml.

Gates :
  G0 PACK      : pack PUR valide (mode=pur, montage_instructions presentes)
  G1 VOD       : yt-dlp disponible + telechargement du segment OK
  G2 DUREE     : duree du clip = duree attendue ± 0.5s
  G3 CODEC     : H.264 (ou VP9) lisible par ffprobe

Usage :
  python3 F00_INGEST/CODEBASE/f00_pur.py --pack pack_pur_A01.json --out OUT/pur
  python3 F00_INGEST/CODEBASE/f00_pur.py --pack ... --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_SEGMENT_SECONDS = 150.0
DURATION_TOLERANCE_SEC = 0.5
ALLOWED_CODECS = {"h264", "vp9", "hevc", "av1"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seconds_to_hms(seconds: float) -> str:
    """737.48 → '00:12:17.480' (format yt-dlp --download-sections)."""
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def load_pack(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def gate_g0_pack(pack: dict) -> tuple[bool, list[str]]:
    """G0 : le pack PUR est exploitable (source + montage_instructions)."""
    errors = []
    if not isinstance(pack, dict):
        return False, ["pack illisible"]
    if pack.get("mode") != "pur":
        errors.append(f"mode={pack.get('mode')!r}, attendu 'pur'")
    source = pack.get("source") or {}
    mi = pack.get("montage_instructions") or {}
    segment = mi.get("segment") or source
    vod_url = segment.get("source_url") or source.get("vod_url")
    if not vod_url:
        errors.append("vod_url absente (source.vod_url / montage_instructions.segment.source_url)")
    if source.get("start_sec") is None and segment.get("start_sec") is None:
        errors.append("start_sec absent")
    if source.get("end_sec") is None and segment.get("end_sec") is None:
        errors.append("end_sec absent")
    start = float(source.get("start_sec") if source.get("start_sec") is not None else segment.get("start_sec") or 0)
    end = float(source.get("end_sec") if source.get("end_sec") is not None else segment.get("end_sec") or 0)
    if end <= start:
        errors.append(f"segment invalide : end ({end}) <= start ({start})")
    if end - start > MAX_SEGMENT_SECONDS:
        errors.append(f"segment trop long ({end - start:.1f}s > {MAX_SEGMENT_SECONDS}s)")
    if not mi:
        errors.append("montage_instructions absente")
    return len(errors) == 0, errors


def build_ytdlp_command(vod_url: str, start: float, end: float, out_path: Path) -> list[str]:
    """Commande yt-dlp sectionnée — identique à la doctrine F00B_VOX."""
    return [
        "yt-dlp",
        "--download-sections", f"*{seconds_to_hms(start)}-{seconds_to_hms(end)}",
        "--force-keyframes-at-cuts",
        "-f", "bv*[height<=1080]+ba/b",
        "--concurrent-fragments", "5",
        "--no-playlist",
        "-o", str(out_path),
        vod_url,
    ]


def probe_clip(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,codec_type,width,height:format=duration",
        "-of", "json", str(path),
    ]
    data = json.loads(subprocess.check_output(cmd, text=True))
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    duration = float(data.get("format", {}).get("duration") or 0)
    return {
        "codec": video.get("codec_name") if video else None,
        "width": int(video.get("width") or 0) if video else 0,
        "height": int(video.get("height") or 0) if video else 0,
        "duration_seconds": round(duration, 3),
    }


def find_downloaded_file(out_dir: Path) -> Path | None:
    """yt-dlp choisit l'extension (mp4/mkv/webm) — retrouve le fichier produit."""
    candidates = [p for p in out_dir.iterdir() if p.is_file()] if out_dir.exists() else []
    for ext_priority in (".mp4", ".mkv", ".webm"):
        for c in candidates:
            if c.suffix.lower() == ext_priority:
                return c
    return candidates[0] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description="F00-PUR : ingest segment VOD depuis un pack PUR")
    parser.add_argument("--pack", type=Path, required=True, help="production_pack_pur_*.json")
    parser.add_argument("--out", type=Path, required=True, help="Dossier de sortie (clips + manifeste)")
    parser.add_argument("--clip-name", default=None, help="Nom du clip (défaut: pur_<angle_id>.mp4)")
    parser.add_argument("--dry-run", action="store_true", help="Valide G0 et affiche la commande sans télécharger")
    args = parser.parse_args()

    print(f"\n═══ F00-PUR — {now()} ═══")
    pack = load_pack(args.pack)

    # ── G0 PACK ──
    ok, errors = gate_g0_pack(pack)
    if not ok:
        for e in errors:
            print(f"  [✗] G0 PACK : {e}")
        print("\n═══ CONTRÔLE G0 : ✗ ÉCHOUÉ ═══")
        return 1
    print("  [✓] G0 PACK : pack PUR valide")

    mi = pack["montage_instructions"]
    segment = mi.get("segment") or pack.get("source") or {}
    vod_url = segment.get("source_url") or pack["source"].get("vod_url")
    start = float(segment.get("start_sec") if segment.get("start_sec") is not None else pack["source"]["start_sec"])
    end = float(segment.get("end_sec") if segment.get("end_sec") is not None else pack["source"]["end_sec"])
    expected_duration = end - start
    angle_id = (pack.get("identite") or {}).get("angle_id") or pack.get("pack_id") or "clip"
    clip_name = args.clip_name or f"pur_{angle_id}.mp4"

    cmd = build_ytdlp_command(vod_url, start, end, Path(clip_name))
    print(f"  Segment : {seconds_to_hms(start)} → {seconds_to_hms(end)} ({expected_duration:.1f}s)")
    print(f"  VOD     : {vod_url}")

    if args.dry_run:
        print("  [dry-run] " + " ".join(cmd))
        print("\n═══ DRY-RUN G0 : ✓ VALIDÉ (aucun téléchargement) ═══")
        return 0

    # ── G1 VOD ──
    if shutil.which("yt-dlp") is None:
        print("  [✗] G1 VOD : yt-dlp introuvable (pip install yt-dlp)")
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    out_pattern = args.out / clip_name.replace(".mp4", "")
    cmd = build_ytdlp_command(vod_url, start, end, out_pattern)
    print("  [..] G1 VOD : téléchargement du segment…")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
    except subprocess.CalledProcessError as exc:
        print(f"  [✗] G1 VOD : échec yt-dlp\n{exc.stderr[-800:] if exc.stderr else exc}")
        return 1
    downloaded = find_downloaded_file(args.out)
    if downloaded is None:
        print("  [✗] G1 VOD : aucun fichier produit par yt-dlp")
        return 1
    print(f"  [✓] G1 VOD : {downloaded.name} ({downloaded.stat().st_size / 1e6:.1f} Mo)")

    # Normalise en .mp4 (H.264) si yt-dlp a produit un conteneur exotique
    clip_path = args.out / clip_name
    if downloaded.suffix.lower() != ".mp4":
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(downloaded),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-c:a", "aac", "-b:a", "192k", str(clip_path)],
            check=True)
        downloaded.unlink()
    else:
        shutil.move(str(downloaded), str(clip_path))

    # ── G2 DUREE ──
    meta = probe_clip(clip_path)
    if abs(meta["duration_seconds"] - expected_duration) > DURATION_TOLERANCE_SEC:
        print(f"  [✗] G2 DUREE : {meta['duration_seconds']}s ≠ {expected_duration}s ±{DURATION_TOLERANCE_SEC}")
        return 1
    print(f"  [✓] G2 DUREE : {meta['duration_seconds']}s (attendu {expected_duration}s)")

    # ── G3 CODEC ──
    if meta["codec"] not in ALLOWED_CODECS:
        print(f"  [✗] G3 CODEC : {meta['codec']} non lisible")
        return 1
    print(f"  [✓] G3 CODEC : {meta['codec']} {meta['width']}x{meta['height']}")

    # ── Manifeste pur_sources.json ──
    sources = {
        "schema_version": "dev10.pur-sources.v1",
        "generated_at": now(),
        "pack_id": pack.get("pack_id"),
        "angle_id": angle_id,
        "vod_url": vod_url,
        "start_sec": start,
        "end_sec": end,
        "expected_duration_sec": expected_duration,
        "clip_file": f"clips/{clip_name}",
        "probe": meta,
        "gates": {"G0": "PASSED", "G1": "PASSED", "G2": "PASSED", "G3": "PASSED"},
    }
    (args.out / "pur_sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    print(f"\n═══ F00-PUR : ✓ MISSION ACCOMPLIE — {clip_path} ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
