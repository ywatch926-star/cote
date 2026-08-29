"""
LAC_F04_SIGNUM — Frégate F04
Mission : Post-production FFmpeg — filtres visuels + finalisation livrable
Technologie : FFmpeg (subprocess)
Loi d'isolement : accès à F04/IN/ et F04/OUT/ uniquement
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ─── CONFIGURATION ────────────────────────────────────────────────────────────

TOLERANCE_FRAMES  = 2     # Tolérance écart durée vidéo/timing (frames)
GRAIN_NOISE_SCALE = 50    # grain_overlay_opacity (0-1) → FFmpeg noise (0-50)
PREVIEW_QUALITY   = 2     # JPEG quality pour preview (1=max, 31=min)


# ─── DÉPENDANCES ──────────────────────────────────────────────────────────────

def check_dependencies() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(
                f"[SIGNUM] {tool} introuvable. Installer : apt-get install -y ffmpeg"
            )
    print("[SIGNUM] FFmpeg et ffprobe détectés.")


# ─── FFPROBE ──────────────────────────────────────────────────────────────────

def get_video_duration(path: str) -> float:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe échoué : {r.stderr}")
    return float(json.loads(r.stdout)["format"]["duration"])


def get_video_info(path: str) -> dict:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
           "-show_streams", "-show_format", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe échoué : {r.stderr}")
    return json.loads(r.stdout)


# ─── CREATIVE CONFIG ──────────────────────────────────────────────────────────

def load_creative_config(config_path: str) -> dict:
    """Charge creative_config.json avec valeurs par défaut si absent."""
    defaults = {
        "grain_overlay_opacity": 0.0,
        "css_filters": "contrast(1.0) brightness(1.0) sepia(0.0)"
    }
    p = Path(config_path)
    if not p.exists():
        print(f"[SIGNUM] creative_config.json absent — filtres désactivés.")
        return defaults
    with open(p, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    defaults.update(cfg)
    print(f"[SIGNUM] creative_config.json chargé.")
    return defaults


def parse_css_filters(css_str: str) -> dict:
    """Parse 'contrast(1.2) brightness(0.88) sepia(0.15)' → dict."""
    result = {"contrast": 1.0, "brightness": 1.0, "sepia": 0.0}
    for key in result:
        m = re.search(rf'{key}\(([\d.]+)\)', css_str or '')
        if m:
            result[key] = float(m.group(1))
    return result


def build_vf_filter(cfg: dict) -> str | None:
    """Construit le filtergraph FFmpeg à partir des valeurs creative_config."""
    grain = float(cfg.get("grain_overlay_opacity", 0.0))
    css   = parse_css_filters(cfg.get("css_filters", ""))

    filters = []

    # 1. eq : contrast + brightness
    # CSS brightness(x) est multiplicatif. FFmpeg eq brightness est additif (-1..1).
    # Approximation linéaire : (css_b - 1.0) * 0.5
    contrast          = css["contrast"]
    ffmpeg_brightness = (css["brightness"] - 1.0) * 0.5

    if abs(contrast - 1.0) > 0.001 or abs(ffmpeg_brightness) > 0.001:
        filters.append(
            f"eq=contrast={contrast:.3f}:brightness={ffmpeg_brightness:.3f}"
        )

    # 2. sepia via colorbalance (teinte chaude rouge/jaune, réduction bleu)
    sepia = css["sepia"]
    if sepia > 0.005:
        rs = round( sepia * 0.20, 3)
        bs = round(-sepia * 0.15, 3)
        filters.append(
            f"colorbalance=rs={rs}:gs=0:bs={bs}"
            f":rm={round(rs*0.6,3)}:gm=0:bm={round(bs*0.6,3)}"
        )

    # 3. grain (noise temporel + uniforme)
    if grain > 0.005:
        ns = max(1, min(int(grain * GRAIN_NOISE_SCALE), 50))
        filters.append(f"noise=c0s={ns}:c0f=t+u")

    return ",".join(filters) if filters else None


def print_filter_summary(cfg: dict, vf: str | None) -> None:
    css   = parse_css_filters(cfg.get("css_filters", ""))
    grain = float(cfg.get("grain_overlay_opacity", 0.0))
    print("──────────────────────────────────────")
    print(f"  grain        : {grain:.2f}  (noise ≈ {int(grain*GRAIN_NOISE_SCALE)})")
    print(f"  contrast     : {css['contrast']:.3f}")
    print(f"  brightness   : {css['brightness']:.3f}")
    print(f"  sepia        : {css['sepia']:.3f}")
    print(f"  filtergraph  : {vf or '(aucun — remux copy)'}")
    print("──────────────────────────────────────")


# ─── PREVIEW FRAME ────────────────────────────────────────────────────────────

def preview_frame(input_mp4: str, vf_filter: str | None, output_dir: str) -> tuple:
    """
    Extrait la frame centrale du MP4.
    Retourne (before_path, after_path) — JPEGs.
    """
    duration  = get_video_duration(input_mp4)
    midpoint  = duration / 2
    out       = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    before = out / "preview_before.jpg"
    after  = out / "preview_after.jpg"

    # Frame originale
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(midpoint), "-i", input_mp4,
         "-vframes", "1", "-q:v", str(PREVIEW_QUALITY), str(before)],
        capture_output=True
    )

    # Frame filtrée
    if vf_filter:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(midpoint), "-i", input_mp4,
             "-vframes", "1", "-vf", vf_filter,
             "-q:v", str(PREVIEW_QUALITY), str(after)],
            capture_output=True
        )
    else:
        shutil.copy(str(before), str(after))

    return str(before), str(after)


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def finalize(
    input_mp4:       str,
    timing_json:     str,
    output_mp4:      str,
    creative_config: str  = None,
    title:           str  = "LACRIMAE",
    comment:         str  = "For the Angel's Tears shall become gold. — Ad Victoriam.",
    # Overrides optionnels (passés depuis le notebook)
    override_grain:      float = None,
    override_contrast:   float = None,
    override_brightness: float = None,
    override_sepia:      float = None,
) -> bool:
    """
    Post-production FFmpeg :
    - Vérification durée vs timing.json
    - Application filtres (grain, contrast, brightness, sepia)
    - Re-encodage h264 si filtres actifs, stream copy sinon
    - Injection métadonnées + faststart
    """
    input_path  = Path(input_mp4)
    output_path = Path(output_mp4)

    # ── Timing ───────────────────────────────────────────────────────────────
    with open(timing_json, "r", encoding="utf-8") as f:
        timing = json.load(f)
    expected = timing["audio_duration_s"]
    fps      = timing.get("fps", 30)

    print(f"[SIGNUM] Durée attendue : {expected:.4f}s")
    actual = get_video_duration(str(input_path))
    print(f"[SIGNUM] Durée réelle   : {actual:.4f}s")
    diff = abs(actual - expected) * fps
    print(f"[SIGNUM] Écart          : {diff:.1f} frames (tolérance : {TOLERANCE_FRAMES})")
    if diff > TOLERANCE_FRAMES:
        print(f"[SIGNUM] AVERTISSEMENT — écart hors tolérance ({diff:.1f} frames)")

    # ── Infos source ─────────────────────────────────────────────────────────
    info = get_video_info(str(input_path))
    vs = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    as_ = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if vs:
        print(f"[SIGNUM] Vidéo : {vs['width']}x{vs['height']} "
              f"@ {vs.get('r_frame_rate', '?')} — {vs['codec_name']}")
    if as_:
        print(f"[SIGNUM] Audio : {as_['codec_name']} — {as_.get('sample_rate', '?')}Hz")
    if vs and (int(vs.get("width", 0)) != 1080 or int(vs.get("height", 0)) != 1920):
        print(f"[SIGNUM] AVERTISSEMENT — résolution inattendue : "
              f"{vs['width']}x{vs['height']}")

    # ── Creative config + overrides ──────────────────────────────────────────
    cfg = load_creative_config(creative_config) if creative_config else {
        "grain_overlay_opacity": 0.0,
        "css_filters": "contrast(1.0) brightness(1.0) sepia(0.0)"
    }

    # Appliquer les overrides si fournis
    if override_grain is not None:
        cfg["grain_overlay_opacity"] = override_grain
    if any(v is not None for v in [override_contrast, override_brightness, override_sepia]):
        css = parse_css_filters(cfg.get("css_filters", ""))
        if override_contrast   is not None: css["contrast"]   = override_contrast
        if override_brightness is not None: css["brightness"] = override_brightness
        if override_sepia      is not None: css["sepia"]      = override_sepia
        cfg["css_filters"] = (
            f"contrast({css['contrast']}) "
            f"brightness({css['brightness']}) "
            f"sepia({css['sepia']})"
        )

    vf = build_vf_filter(cfg)
    print_filter_summary(cfg, vf)

    # ── FFmpeg ───────────────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    if vf:
        # Re-encodage nécessaire pour appliquer les filtres
        cmd += ["-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "fast"]
    else:
        # Aucun filtre → stream copy
        cmd += ["-c:v", "copy"]

    cmd += [
        "-c:a", "copy",
        "-metadata", f"title={title}",
        "-metadata", "artist=LACRIMAE",
        "-metadata", f"comment={comment}",
        "-metadata", "year=2026",
        "-movflags", "faststart",
        str(output_path),
    ]

    print(f"\n[SIGNUM] Lancement FFmpeg...")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"[SIGNUM] ERREUR FFmpeg — code : {result.returncode}")
        return False

    if not output_path.exists():
        print("[SIGNUM] ERREUR — short_master.mp4 non créé.")
        return False

    final_size     = output_path.stat().st_size
    final_duration = get_video_duration(str(output_path))
    print(f"\n[SIGNUM] short_master.mp4 produit :")
    print(f"  Chemin : {output_path}")
    print(f"  Taille : {final_size / 1_000_000:.1f} Mo")
    print(f"  Durée  : {final_duration:.4f}s (attendu {expected:.4f}s)")
    print("[SIGNUM] ✓ Mission accomplie.")
    return True


# ─── POINT D'ENTRÉE ───────────────────────────────────────────────────────────

def main():
    check_dependencies()
    base = Path("/content/drive/MyDrive/DRIVE_LACRIMAE")

    input_mp4        = str(base / "F04_SIGNUM/IN/short_final.mp4")
    timing_json      = str(base / "F04_SIGNUM/IN/timing.json")
    creative_config  = str(base / "F04_SIGNUM/IN/creative_config.json")
    output_mp4       = str(base / "F04_SIGNUM/OUT/short_master.mp4")

    for p in [input_mp4, timing_json]:
        if not Path(p).exists():
            print(f"[SIGNUM] ERREUR : introuvable → {p}")
            sys.exit(1)

    ok = finalize(input_mp4, timing_json, output_mp4, creative_config)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
