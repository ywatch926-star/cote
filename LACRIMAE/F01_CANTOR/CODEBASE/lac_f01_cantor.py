"""
LAC_F01_CANTOR — Frégate F01
Mission : Transcription audio → timing JSON mot par mot
Technologie : faster-whisper
Loi d'isolement : accès à SHARED/audio_clean.mp3 uniquement
"""

import json
import os
import subprocess
import sys
import math
from pathlib import Path


# ─── CONFIGURATION ────────────────────────────────────────────────────────────

FPS = 30

# Mots forts — à enrichir selon le style de chaque campagne
STRONG_WORDS = {
    "larmes", "tears", "sang", "blood", "lumière", "light",
    "ange", "angel", "silence", "mort", "death", "vie", "life",
    "amour", "love", "nuit", "night", "feu", "fire", "or", "gold",
    "âme", "soul", "dieu", "god", "roi", "king", "reine", "queen",
    "eternel", "eternal", "sacré", "sacred", "ombre", "shadow",
    "gloire", "glory", "chute", "fall", "victoire", "victory",
    "douleur", "pain", "espoir", "hope", "destin", "destiny",
    "sanguinius", "primarch", "emperor", "chaos", "warp",
}


# ─── TRANSCRIPTION ────────────────────────────────────────────────────────────

def transcribe(audio_path: str, model_size: str = "medium", model_language: str = "fr") -> dict:
    """
    Transcrit l'audio via faster-whisper.
    Retourne le timing JSON complet.

    Args:
        audio_path     : chemin vers le fichier audio
        model_size     : taille du modèle Whisper ('tiny','base','small','medium','large-v3')
        model_language : code langue ISO (ex: 'fr', 'en', 'es'). None = détection auto.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[CANTOR] Installation de faster-whisper...")
        # FIX: utiliser subprocess.check_call pour détecter les erreurs d'installation
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "faster-whisper", "-q"],
            stderr=subprocess.DEVNULL,
        )
        from faster_whisper import WhisperModel

    # FIX: détection dynamique CUDA → fallback CPU automatique
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
            compute_type = "float16"
            print("[CANTOR] GPU CUDA détecté — mode float16.")
        else:
            device = "cpu"
            compute_type = "int8"
            print("[CANTOR] Pas de GPU détecté — mode CPU int8 (plus lent).")
    except ImportError:
        # torch non disponible — on tente cuda, faster-whisper gérera le fallback
        device = "auto"
        compute_type = "int8"
        print("[CANTOR] torch non disponible — device=auto.")

    print(f"[CANTOR] Chargement du modèle Whisper '{model_size}' ({device})...")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    print(f"[CANTOR] Transcription de : {audio_path}")
    segments, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        language=model_language,          # FIX: paramétrable, None = auto-detect
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )

    audio_duration_s = info.duration
    total_frames = math.ceil(audio_duration_s * FPS)

    print(f"[CANTOR] Durée audio : {audio_duration_s:.2f}s → {total_frames} frames @ {FPS}fps")

    words = []
    for segment in segments:
        if not hasattr(segment, "words") or segment.words is None:
            continue
        for w in segment.words:
            word_clean = w.word.strip().lower().rstrip(".,!?;:\"'")
            is_strong = word_clean in STRONG_WORDS

            start_frame = math.floor(w.start * FPS)
            end_frame = math.ceil(w.end * FPS)

            # Garantie : end_frame > start_frame
            if end_frame <= start_frame:
                end_frame = start_frame + 1

            words.append({
                "word": w.word.strip(),
                "start_s": round(w.start, 4),
                "end_s": round(w.end, 4),
                "start_frame": start_frame,
                "end_frame": end_frame,
                "is_strong": is_strong,
            })

    print(f"[CANTOR] {len(words)} mots transcrits.")

    return {
        "audio_duration_s": round(audio_duration_s, 4),
        "total_frames": total_frames,
        "fps": FPS,
        "words": words,
    }


# ─── VALIDATION INTERNE ───────────────────────────────────────────────────────

def validate_timing(timing: dict) -> bool:
    """Validation minimale du timing produit avant écriture."""
    required_keys = {"audio_duration_s", "total_frames", "fps", "words"}
    if not required_keys.issubset(timing.keys()):
        print("[CANTOR] ERREUR : clés manquantes dans le timing.")
        return False

    if len(timing["words"]) == 0:
        print("[CANTOR] ERREUR : aucun mot transcrit.")
        return False

    for i, w in enumerate(timing["words"]):
        if w["end_frame"] <= w["start_frame"]:
            print(f"[CANTOR] ERREUR : mot {i} — end_frame <= start_frame : {w}")
            return False

    print(f"[CANTOR] Validation interne OK — {len(timing['words'])} mots, {timing['audio_duration_s']}s.")
    return True


# ─── ÉCRITURE OUTPUT ──────────────────────────────────────────────────────────

def write_output(timing: dict, out_path: str) -> None:
    """Ecrit le timing JSON dans OUT/timing.json."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False, indent=2)
    print(f"[CANTOR] timing.json écrit → {out_path}")


# ─── POINT D'ENTRÉE ───────────────────────────────────────────────────────────

def main():
    # Chemins Colab/Drive standards
    base = Path("/content/drive/MyDrive/DRIVE_LACRIMAE")
    audio_path = str(base / "SHARED" / "audio_clean.mp3")
    out_path = str(base / "F01_CANTOR" / "OUT" / "timing.json")

    # Override via arguments CLI si nécessaire
    if len(sys.argv) >= 2:
        audio_path = sys.argv[1]
    if len(sys.argv) >= 3:
        out_path = sys.argv[2]

    if not Path(audio_path).exists():
        print(f"[CANTOR] ERREUR : audio introuvable → {audio_path}")
        sys.exit(1)

    timing = transcribe(audio_path)

    if not validate_timing(timing):
        print("[CANTOR] ÉCHEC — timing invalide, aucune écriture.")
        sys.exit(1)

    write_output(timing, out_path)
    print("[CANTOR] ✓ Mission accomplie — timing.json prêt pour LAC_CUSTOS.")


if __name__ == "__main__":
    main()
