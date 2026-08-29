"""
LAC_CUSTOS — Gardien de la Flotte LACRIMAE
Mission : Validation inter-frégates — vérifie l'intégrité des inputs/outputs
          avant et après chaque transit manuel.

LOIS :
  - stdlib Python uniquement (pas de dépendances externes)
  - Jamais de déplacement de fichiers (LOI D'ISOLEMENT)
  - Retourne exit code 0 si validation OK, 1 si échec

Usage :
  python LAC_CUSTOS.py --frigate F01 --mode check-out [--drive-base /path]
  python LAC_CUSTOS.py --frigate F02 --mode check-in  [--drive-base /path]
"""

import argparse
import json
import os
import sys
from pathlib import Path


# ─── CONFIGURATION ────────────────────────────────────────────────────────────

DEFAULT_DRIVE_BASE = "/content/drive/MyDrive/DRIVE_LACRIMAE"

# Manifeste des fichiers attendus par frégate
MANIFEST = {
    "F01": {
        "check-out": {
            "OUT": ["timing.json"],
        },
        "check-in": {
            "IN": ["audio_clean.mp3"],
        },
    },
    "F02": {
        "check-out": {
            "OUT": ["creative_config.json"],
        },
        "check-in": {
            "IN": ["timing.json"],
            "IN/images": [],  # dossier doit exister avec au moins 1 image
        },
    },
    "F03": {
        "check-out": {
            "OUT": ["short_final.mp4"],
        },
        "check-in": {
            "IN": ["timing.json", "creative_config.json", "audio_clean.mp3"],
            "IN/images": [],
        },
    },
    "F04": {
        "check-out": {
            "OUT": ["short_master.mp4"],
        },
        "check-in": {
            "IN": ["short_final.mp4", "timing.json"],
        },
    },
}

# Validateurs de contenu JSON par fichier
JSON_VALIDATORS = {
    "timing.json": ["audio_duration_s", "total_frames", "fps", "words"],
    "creative_config.json": [
        "fps", "resolution", "cut_interval_frames", "font_main",
        "font_strong", "grain_overlay_opacity", "validated_by_magos"
    ],
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


# ─── UTILITAIRES ──────────────────────────────────────────────────────────────

def log_ok(msg: str) -> None:
    print(f"  [✓] {msg}")

def log_err(msg: str) -> None:
    print(f"  [✗] {msg}")

def log_warn(msg: str) -> None:
    print(f"  [!] {msg}")

def log_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ─── VALIDATEURS ──────────────────────────────────────────────────────────────

def check_file_exists(path: Path) -> bool:
    if path.exists() and path.is_file():
        size = path.stat().st_size
        log_ok(f"{path.name} — {size} octets")
        return True
    log_err(f"{path.name} — INTROUVABLE ({path})")
    return False


def check_json_content(path: Path) -> bool:
    """Valide le contenu JSON d'un fichier selon son manifeste."""
    filename = path.name
    if filename not in JSON_VALIDATORS:
        return True  # Pas de règle de contenu → skip

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log_err(f"{filename} — JSON invalide : {e}")
        return False

    required_keys = JSON_VALIDATORS[filename]
    missing = [k for k in required_keys if k not in data]
    if missing:
        log_err(f"{filename} — Clés manquantes : {missing}")
        return False

    # Vérifications spécifiques timing.json
    if filename == "timing.json":
        if not isinstance(data.get("words"), list):
            log_err("timing.json — 'words' doit être une liste")
            return False
        if len(data["words"]) == 0:
            log_err("timing.json — 'words' est vide")
            return False
        if data.get("fps") != 30:
            log_warn(f"timing.json — fps={data.get('fps')} (attendu 30)")
        log_ok(f"timing.json — {len(data['words'])} mots, {data['audio_duration_s']}s")

    # Vérifications spécifiques creative_config.json
    if filename == "creative_config.json":
        if not data.get("validated_by_magos"):
            log_err("creative_config.json — 'validated_by_magos' doit être true")
            return False
        log_ok(f"creative_config.json — validé par le Magos")

    return True


def check_images_dir(path: Path) -> bool:
    """Vérifie qu'un dossier contient au moins 1 image valide."""
    if not path.exists() or not path.is_dir():
        log_err(f"Dossier images introuvable : {path}")
        return False
    images = [f for f in path.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]
    if len(images) == 0:
        log_err(f"Dossier images vide : {path}")
        return False
    log_ok(f"images/ — {len(images)} image(s) trouvée(s)")
    return True


def check_mp4_non_empty(path: Path) -> bool:
    """Vérifie qu'un fichier .mp4 a une taille plausible (> 100Ko)."""
    if not path.exists():
        return False  # Déjà signalé par check_file_exists
    size = path.stat().st_size
    if size < 100_000:
        log_warn(f"{path.name} — taille suspecte ({size} octets < 100Ko)")
        return False
    return True


# ─── VALIDATION PRINCIPALE ────────────────────────────────────────────────────

def run_custos(frigate: str, mode: str, drive_base: Path) -> bool:
    """
    Lance la validation pour une frégate et un mode donnés.
    Retourne True si tout est OK.
    """
    if frigate not in MANIFEST:
        print(f"[CUSTOS] Frégate inconnue : {frigate}")
        return False
    if mode not in MANIFEST[frigate]:
        print(f"[CUSTOS] Mode inconnu : {mode} pour {frigate}")
        return False

    frigate_dirs = {
        "F01": drive_base / "F01_CANTOR",
        "F02": drive_base / "F02_VISIO",
        "F03": drive_base / "F03_PICTOR",
        "F04": drive_base / "F04_SIGNUM",
    }

    frigate_base = frigate_dirs[frigate]
    rules = MANIFEST[frigate][mode]
    all_ok = True

    log_section(f"LAC_CUSTOS — {frigate} | {mode.upper()}")
    print(f"  Base : {frigate_base}")

    for folder_rel, files in rules.items():
        folder_path = frigate_base / folder_rel

        # Cas dossier images (liste vide = check existence + images)
        if folder_rel.endswith("/images") or folder_rel == "IN/images":
            ok = check_images_dir(folder_path)
            all_ok = all_ok and ok
            continue

        # Vérification de chaque fichier
        for filename in files:
            file_path = folder_path / filename
            ok = check_file_exists(file_path)
            all_ok = all_ok and ok

            if ok and filename.endswith(".json"):
                ok_json = check_json_content(file_path)
                all_ok = all_ok and ok_json

            if ok and filename.endswith(".mp4"):
                ok_mp4 = check_mp4_non_empty(file_path)
                all_ok = all_ok and ok_mp4

    print()
    if all_ok:
        print(f"  ══ CUSTOS VERDICT : ✓ {frigate} {mode.upper()} VALIDÉ ══")
        print(f"  Transit autorisé.\n")
    else:
        print(f"  ══ CUSTOS VERDICT : ✗ {frigate} {mode.upper()} ÉCHOUÉ ══")
        print(f"  Corriger les erreurs avant tout transit.\n")

    return all_ok


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LAC_CUSTOS — Gardien de la Flotte LACRIMAE"
    )
    parser.add_argument(
        "--frigate", required=True, choices=["F01", "F02", "F03", "F04"],
        help="Frégate à valider"
    )
    parser.add_argument(
        "--mode", required=True, choices=["check-in", "check-out"],
        help="check-in = valider les inputs | check-out = valider les outputs"
    )
    parser.add_argument(
        "--drive-base", default=DEFAULT_DRIVE_BASE,
        help=f"Racine Drive LACRIMAE (défaut: {DEFAULT_DRIVE_BASE})"
    )

    args = parser.parse_args()
    drive_base = Path(args.drive_base)

    if not drive_base.exists():
        print(f"[CUSTOS] ERREUR : drive-base introuvable : {drive_base}")
        sys.exit(1)

    ok = run_custos(args.frigate, args.mode, drive_base)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

