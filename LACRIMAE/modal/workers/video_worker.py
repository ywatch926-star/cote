"""Worker Modal GPU pour les frégates vidéo LACRIMAE dev6.

F02_MOTUS exécute RIFE HDv3 depuis le Volume modèles. Les autres étapes
restent contractuelles jusqu'à l'intégration de leurs moteurs respectifs.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import modal

APP_NAME = os.environ.get("LACRIMAE_MODAL_APP", "lacrimae-dev6-video")
VIDEO_DIR = "/data"
MODEL_DIR = "/models"
RIFE_VERSION = "4.25"
RIFE_MODEL_DIR = Path(MODEL_DIR) / "models" / "RIFE" / RIFE_VERSION / "train_log"
ATOM_CONFIG_PATH = Path("/app/CONFIG/atom_ic_profiles.json")
GPU_STAGES = {
    "F02_MOTUS", "F02_MOTUS_RIFE",
    "F03_RESTAURA", "F03_APOTHECA_RESTAURA",
    "F04_UPSCALE", "F04_FORGE_TEXTURA",
    "F05_LIBRARIUS_FACIES",
    "F06_LUMEN", "F06_LUMEN_IGNIS",
    "F07_CHROMA_DOMINATUS", "F08_TEMPORALIS_CONSISTENTIA",
}

image = modal.Image.from_dockerfile("modal/images/Dockerfile.video-gpu")
app = modal.App(APP_NAME)
video_volume = modal.Volume.from_name(
    os.environ.get("LACRIMAE_VIDEO_VOLUME", "lacrimae-dev6-video"),
    create_if_missing=True,
)
model_volume = modal.Volume.from_name(
    os.environ.get("LACRIMAE_MODEL_VOLUME", "lacrimae-dev6-models"),
    create_if_missing=True,
)


def safe_relative(value: str) -> Path:
    raw = value.removeprefix("modal://").lstrip("/")
    path = Path(raw)
    if not raw or path.is_absolute() or ".." in path.parts:
        raise ValueError("le chemin doit être relatif et rester dans le Volume")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_rife():
    """Charge RIFE depuis le Volume, sans téléchargement pendant la mission."""
    required = [
        RIFE_MODEL_DIR / "flownet.pkl",
        RIFE_MODEL_DIR / "IFNet_HDv3.py",
        RIFE_MODEL_DIR / "RIFE_HDv3.py",
        RIFE_MODEL_DIR / "refine.py",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("fichiers RIFE absents du Volume modèles: " + ", ".join(missing))
    runtime_root = Path("/app/rife_runtime")
    if str(runtime_root) not in sys.path:
        sys.path.insert(0, str(runtime_root))
    version_root = str(RIFE_MODEL_DIR.parent)
    if version_root not in sys.path:
        sys.path.insert(0, version_root)
    module = importlib.import_module("train_log.RIFE_HDv3")
    model = module.Model()
    model.load_model(str(RIFE_MODEL_DIR), -1)
    model.eval()
    model.device()
    return model


def _tensor_from_frame(frame_bgr, torch, functional, device, padding):
    import cv2
    import numpy as np
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(np.transpose(rgb, (2, 0, 1))).to(device, non_blocking=True)
    tensor = tensor.unsqueeze(0).float() / 255.0
    return functional.pad(tensor, padding)


def _run_rife(source: Path, destination: Path, target_fps: int) -> dict:
    import cv2
    import numpy as np
    import torch
    import torch.nn.functional as F

    capture = cv2.VideoCapture(str(source))
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if source_fps <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError("métadonnées vidéo invalides")
    multiplier = round(target_fps / source_fps)
    if multiplier < 2 or abs(source_fps * multiplier - target_fps) > 0.01:
        capture.release()
        raise ValueError(
            f"RIFE F02 attend un facteur entier: source={source_fps:.6f}, cible={target_fps}"
        )
    ok, first = capture.read()
    if not ok:
        capture.release()
        raise ValueError("impossible de lire la première image")
    capture.release()

    tmp = destination.with_suffix(destination.suffix + ".silent.tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), float(target_fps), (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError("VideoWriter MP4 indisponible")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = _load_rife()
    process_scale = 0.5 if max(width, height) >= 3000 else 1.0
    block = max(128, int(128 / process_scale))
    padded_h = ((height - 1) // block + 1) * block
    padded_w = ((width - 1) // block + 1) * block
    padding = (0, padded_w - width, 0, padded_h - height)
    previous = _tensor_from_frame(first, torch, F, device, padding)
    written = 0
    started = time.monotonic()

    def write_tensor(tensor):
        nonlocal written
        rgb = (tensor[0, :, :height, :width].clamp(0, 1) * 255.0).byte().cpu().numpy()
        bgr = cv2.cvtColor(np.transpose(rgb, (1, 2, 0)), cv2.COLOR_RGB2BGR)
        writer.write(bgr)
        written += 1

    capture = cv2.VideoCapture(str(source))
    ok, _ = capture.read()
    if not ok:
        capture.release()
        writer.release()
        raise ValueError("impossible de relire la première image")
    with torch.inference_mode():
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            current = _tensor_from_frame(frame, torch, F, device, padding)
            write_tensor(previous)
            for index in range(1, multiplier):
                timestep = index / multiplier
                middle = model.inference(previous, current, timestep, process_scale)
                write_tensor(middle)
            previous = current
        write_tensor(previous)
        capture.release()
    writer.release()
    if written != (frame_count - 1) * multiplier + 1:
        raise RuntimeError(f"nombre d'images inattendu: {written}")
    muxed = destination.with_suffix(destination.suffix + ".audio.tmp.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(source),
         "-map", "0:v:0", "-map", "1:a?", "-c:v", "copy", "-c:a", "copy",
         "-movflags", "+faststart", str(muxed)],
        check=True,
    )
    muxed.replace(destination)
    tmp.unlink(missing_ok=True)
    elapsed = time.monotonic() - started
    torch.cuda.empty_cache() if torch.cuda.is_available() else None
    return {
        "implementation": "rife_hd_v3_4.25",
        "source_fps": source_fps,
        "target_fps": target_fps,
        "multiplier": multiplier,
        "input_frames": frame_count,
        "output_frames": written,
        "resolution": [width, height],
        "audio": "copied_stream_copy",
        "inference_seconds": round(elapsed, 3),
    }


def _run_gfpgan(source: Path, destination: Path, profile: str) -> dict:
    """Restaure les visages détectés sans agrandir l’image et remuxe l’audio."""
    import cv2
    import torch
    import torchvision.transforms.functional as tv_functional
    sys.modules.setdefault("torchvision.transforms.functional_tensor", tv_functional)
    from gfpgan import GFPGANer

    weights = Path(MODEL_DIR) / "models" / "GFPGAN" / "1.3" / "GFPGANv1.3.pth"
    if not weights.is_file():
        raise FileNotFoundError(f"poids GFPGAN absents du Volume modèles: {weights}")
    capture = cv2.VideoCapture(str(source))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError("métadonnées vidéo invalides pour F05")
    atom = _load_atom_profile(profile)
    face_cfg = atom.get("face", {})
    strength = float(face_cfg.get("weight", 0.62)) if face_cfg.get("enabled", True) else 0.0
    strength = max(0.0, min(1.0, strength))
    frame_stride = max(1, int(face_cfg.get("frame_stride", 1)))
    restorer = GFPGANer(
        model_path=str(weights), upscale=1, arch="clean", channel_multiplier=2,
        bg_upsampler=None, device="cuda" if torch.cuda.is_available() else "cpu",
    )
    silent = destination.with_suffix(destination.suffix + ".faces.tmp.mp4")
    writer = cv2.VideoWriter(str(silent), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise RuntimeError("impossible d’ouvrir l’encodeur temporaire F05")
    started = time.monotonic()
    processed = 0
    detected_faces = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if strength > 0.0 and (processed % frame_stride == 0):
            cropped_faces, _, restored = restorer.enhance(
                frame, has_aligned=False, only_center_face=False, paste_back=True,
                weight=strength,
            )
            detected_faces += len(cropped_faces or [])
            if restored is None:
                restored = frame
        else:
            restored = frame
        writer.write(restored)
        processed += 1
    capture.release()
    writer.release()
    if processed != frame_count:
        raise RuntimeError(f"F05 a traité {processed}/{frame_count} images")
    muxed = destination.with_suffix(destination.suffix + ".mux.tmp.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(source),
         "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264", "-preset", "fast",
         "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
         str(muxed)], check=True,
    )
    muxed.replace(destination)
    silent.unlink(missing_ok=True)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {
        "implementation": "gfpgan_v1.3_face_restore_native",
        "model": "GFPGANv1.3",
        "input_resolution": [width, height],
        "output_resolution": [width, height],
        "source_fps": fps,
        "target_fps": fps,
        "input_frames": frame_count,
        "output_frames": processed,
        "faces_detected": detected_faces,
        "frame_stride": frame_stride,
        "audio": "copied_stream_copy",
        "inference_seconds": round(time.monotonic() - started, 3),
    }


def _load_atom_profile(profile: str) -> dict:
    """Charge un profil ATOM-IC embarqué dans l’image, avec repli sûr."""
    if ATOM_CONFIG_PATH.is_file():
        payload = json.loads(ATOM_CONFIG_PATH.read_text(encoding="utf-8"))
        profiles = payload.get("profiles", {})
        if profile in profiles:
            return profiles[profile]
        default_name = payload.get("default_profile", "balanced")
        if default_name in profiles:
            return profiles[default_name]
    return {
        "restaura": {"denoise_luma": 0.8, "denoise_chroma": 0.65, "unsharp_amount": 0.30, "unsharp_radius": 5},
        "textura": {"contrast": 1.08, "saturation": 1.06, "unsharp_amount": 0.40, "unsharp_radius": 5, "local_detail": 0.12},
        "lumen": {"contrast": 1.08, "saturation": 1.06, "brightness": 0.0, "unsharp_amount": 0.34, "unsharp_radius": 5, "highlight_bloom": 0.0},
    }


def _run_ffmpeg_filter(source: Path, destination: Path, stage: str, profile: str) -> dict:
    """Restauration/finalisation ATOM-IC à résolution native, avec audio conservé."""
    import cv2

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,avg_frame_rate,nb_frames", "-of", "json", str(source)],
        check=True, capture_output=True, text=True,
    )
    stream = json.loads(probe.stdout).get("streams", [{}])[0]
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    fps = stream.get("avg_frame_rate") or "0/0"
    if not width or not height:
        raise ValueError(f"métadonnées invalides pour {stage}")

    atom = _load_atom_profile(profile)
    if stage == "F03_RESTAURA":
        cfg = atom["restaura"]
        video_filter = (
            f"hqdn3d={cfg['denoise_luma']}:{cfg['denoise_chroma']}:3:3,"
            f"unsharp={cfg['unsharp_radius']}:{cfg['unsharp_radius']}:{cfg['unsharp_amount']}:"
            f"{cfg['unsharp_radius']}:{cfg['unsharp_radius']}:0"
        )
        implementation = "atom_ic_restaura_native"
    elif stage == "F04_FORGE_TEXTURA":
        cfg = atom["textura"]
        video_filter = (
            f"eq=contrast={cfg['contrast']}:saturation={cfg['saturation']},"
            f"unsharp={cfg['unsharp_radius']}:{cfg['unsharp_radius']}:{cfg['unsharp_amount']}:"
            f"{cfg['unsharp_radius']}:{cfg['unsharp_radius']}:0"
        )
        implementation = "atom_ic_textura_native"
    else:
        cfg = atom["lumen"]
        video_filter = (
            f"eq=contrast={cfg['contrast']}:saturation={cfg['saturation']}:brightness={cfg['brightness']},"
            f"unsharp={cfg['unsharp_radius']}:{cfg['unsharp_radius']}:{cfg['unsharp_amount']}:"
            f"{cfg['unsharp_radius']}:{cfg['unsharp_radius']}:0"
        )
        implementation = "atom_ic_lumen_native"

    tmp = destination.with_suffix(destination.suffix + f".{stage.lower()}.tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
        "-vf", video_filter, "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp),
    ]
    subprocess.run(command, check=True)
    tmp.replace(destination)
    capture = cv2.VideoCapture(str(destination))
    output_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    out_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    capture.release()
    return {
        "implementation": implementation,
        "input_resolution": [width, height],
        "output_resolution": [width, height],
        "source_fps": fps,
        "target_fps": out_fps,
        "output_frames": output_frames,
        "audio": "copied_stream_copy",
        "inference_seconds": round(time.monotonic() - started, 3),
    }


def _run_chroma(source: Path, destination: Path, profile: str) -> dict:
    """Applique la finition colorimétrique ATOM-IC à résolution native."""
    import cv2
    atom = _load_atom_profile(profile)
    cfg = atom.get("chroma", {})
    video_filter = (
        f"eq=contrast={cfg.get('contrast', 1.08)}:brightness={cfg.get('brightness', 0.0)}:"
        f"saturation={cfg.get('saturation', 1.08)}:gamma={cfg.get('gamma', 1.0)},"
        f"colorbalance=rs={cfg.get('red_shadow', 0.0)}:gs={cfg.get('green_shadow', 0.0)}:"
        f"bs={cfg.get('blue_shadow', 0.0)}:rm={cfg.get('red_mid', 0.0)}:"
        f"gm={cfg.get('green_mid', 0.0)}:bm={cfg.get('blue_mid', 0.0)}"
    )
    tmp = destination.with_suffix(destination.suffix + ".chroma.tmp.mp4")
    started = time.monotonic()
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-vf", video_filter,
        "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp)
    ], check=True)
    tmp.replace(destination)
    capture = cv2.VideoCapture(str(destination))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.release()
    return {"implementation": "atom_ic_chroma_dominatus", "input_resolution": [width, height],
            "output_resolution": [width, height], "source_fps": fps, "target_fps": fps,
            "output_frames": frames, "audio": "copied_stream_copy",
            "inference_seconds": round(time.monotonic() - started, 3)}


def _run_temporal_consistency(source: Path, destination: Path, profile: str) -> dict:
    """Passe temporelle conservatrice ; copie sans mélange lorsque le profil la désactive."""
    import shutil
    atom = _load_atom_profile(profile)
    strength = float(atom.get("temporal", {}).get("strength", 0.0))
    motus = atom.get("motus", {})
    blend = max(0.0, min(1.0, float(motus.get("frame_blend", 0.0))))
    blur = max(0.0, min(1.0, float(motus.get("motion_blur", 0.0))))
    if strength <= 0.0 and blend <= 0.0 and blur <= 0.0:
        shutil.copy2(source, destination)
        return {"implementation": "atom_ic_temporal_guard_passthrough", "temporal_strength": 0.0, "motus_mode": motus.get("mode", "cinematic")}
    tmp = destination.with_suffix(destination.suffix + ".temporal.tmp.mp4")
    opacity = max(blend, min(1.0, strength))
    filters = [f"tblend=all_mode=average:all_opacity={opacity}"]
    if blur > 0.0:
        filters.append(f"tmix=frames=3:weights=1 2 1:scale=4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-vf",
                     ",".join(filters), "-map", "0:v:0", "-map", "0:a?",
                     "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                     "-c:a", "copy", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(destination)
    return {"implementation": "atom_ic_temporal_motus_guard", "temporal_strength": opacity,
            "motus_mode": motus.get("mode", "cinematic"), "motion_blur": blur,
            "frame_blend": blend, "audio": "copied_stream_copy"}


def _run_realesrgan(source: Path, destination: Path) -> dict:
    import cv2
    import torch
    import torchvision.transforms.functional as tv_functional
    sys.modules.setdefault("torchvision.transforms.functional_tensor", tv_functional)
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    weights = Path(MODEL_DIR) / "models" / "RealESRGAN" / "0.1.0" / "RealESRGAN_x4plus.pth"
    if not weights.is_file():
        raise FileNotFoundError(f"poids Real-ESRGAN absents du Volume modèles: {weights}")
    capture = cv2.VideoCapture(str(source))
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if source_fps <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError("métadonnées vidéo invalides pour F04")
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    upsampler = RealESRGANer(
        scale=4, model_path=str(weights), model=model, tile=512, tile_pad=16,
        pre_pad=0, half=torch.cuda.is_available(), gpu_id=0 if torch.cuda.is_available() else None,
    )
    out_w, out_h = width * 2, height * 2
    tmp = destination.with_suffix(destination.suffix + ".upscale.tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), source_fps, (out_w, out_h))
    if not writer.isOpened():
        capture.release()
        raise RuntimeError("VideoWriter 4K indisponible")
    started = time.monotonic()
    processed = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        output, _ = upsampler.enhance(frame, outscale=2)
        if output.shape[1] != out_w or output.shape[0] != out_h:
            output = cv2.resize(output, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
        writer.write(output)
        processed += 1
    capture.release()
    writer.release()
    if processed != frame_count:
        raise RuntimeError(f"nombre d'images inattendu dans F04: {processed}/{frame_count}")
    tmp.replace(destination)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {
        "implementation": "realesrgan_x4plus_outscale_2",
        "source_fps": source_fps,
        "target_fps": source_fps,
        "input_frames": frame_count,
        "output_frames": processed,
        "input_resolution": [width, height],
        "output_resolution": [out_w, out_h],
        "audio": "not_copied_in_f04_mvp",
        "inference_seconds": round(time.monotonic() - started, 3),
    }


@app.function(
    image=image,
    gpu=os.environ.get("LACRIMAE_GPU", "L4"),
    volumes={VIDEO_DIR: video_volume, MODEL_DIR: model_volume},
    timeout=60 * 60,
    retries=1,
)
def run_stage(
    stage: str,
    input_uri: str,
    output_uri: str,
    campaign_id: str,
    profile: str = "balanced",
    target_fps: int = 120,
) -> dict:
    if stage not in GPU_STAGES:
        raise ValueError(f"stage GPU non supporté: {stage}")
    if not input_uri or not output_uri or not campaign_id:
        raise ValueError("input_uri, output_uri et campaign_id sont obligatoires")
    source = Path(VIDEO_DIR) / safe_relative(input_uri)
    destination = Path(VIDEO_DIR) / safe_relative(output_uri)
    if source == destination:
        raise ValueError("entrée et sortie doivent être différentes")
    if not source.is_file():
        raise FileNotFoundError(f"entrée absente du Volume vidéo: {input_uri}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    if stage in ("F02_MOTUS", "F02_MOTUS_RIFE"):
        metrics = _run_rife(source, destination, target_fps)
    elif stage in ("F03_RESTAURA", "F03_APOTHECA_RESTAURA"):
        metrics = _run_ffmpeg_filter(source, destination, "F03_RESTAURA", profile)
    elif stage == "F04_UPSCALE":
        metrics = _run_realesrgan(source, destination)
    elif stage == "F04_FORGE_TEXTURA":
        metrics = _run_ffmpeg_filter(source, destination, "F04_FORGE_TEXTURA", profile)
    elif stage == "F05_LIBRARIUS_FACIES":
        metrics = _run_gfpgan(source, destination, profile)
    elif stage in ("F06_LUMEN", "F06_LUMEN_IGNIS"):
        metrics = _run_ffmpeg_filter(source, destination, "F06_LUMEN", profile)
    elif stage == "F07_CHROMA_DOMINATUS":
        metrics = _run_chroma(source, destination, profile)
    elif stage == "F08_TEMPORALIS_CONSISTENTIA":
        metrics = _run_temporal_consistency(source, destination, profile)
    else:
        import shutil
        shutil.copy2(source, destination)
        metrics = {"implementation": "modal_volume_contract_copy_v1"}
    report = {
        "status": "SUCCEEDED",
        "stage": stage,
        "campaign_id": campaign_id,
        "input_uri": input_uri,
        "output_uri": output_uri,
        "profile": profile,
        "model": ("rife-4.25-hdv3" if stage in ("F02_MOTUS", "F02_MOTUS_RIFE") else "realesrgan-x4plus-0.1.0" if stage == "F04_UPSCALE" else "gfpgan-v1.3" if stage == "F05_LIBRARIUS_FACIES" else None),
        "model_dir": str(RIFE_MODEL_DIR) if stage in ("F02_MOTUS", "F02_MOTUS_RIFE") else str(Path(MODEL_DIR) / "models" / "RealESRGAN" / "0.1.0") if stage == "F04_UPSCALE" else str(Path(MODEL_DIR) / "models" / "GFPGAN" / "1.3") if stage == "F05_LIBRARIUS_FACIES" else MODEL_DIR,
        "output_size_bytes": destination.stat().st_size,
        "output_sha256": sha256(destination),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        **metrics,
    }
    report_path = destination.with_suffix(destination.suffix + ".report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    video_volume.commit()
    return report


@app.local_entrypoint()
def main(
    stage: str = "F02_MOTUS",
    input_uri: str = "",
    output_uri: str = "",
    campaign_id: str = "",
    profile: str = "balanced",
    target_fps: int = 120,
):
    print(run_stage.remote(stage, input_uri, output_uri, campaign_id, profile, target_fps))
