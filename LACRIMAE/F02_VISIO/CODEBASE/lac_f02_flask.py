"""
LAC_F02_VISIO — Frégate F02
Mission : Serveur Flask — viewer interactif preview + production de creative_config.json
Technologie : Flask + port forwarding Colab natif
Loi d'isolement : accès à F02/IN/ uniquement
"""

import json
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_file, after_this_request

app = Flask(__name__)

# ─── CORS (FIX: nécessaire pour Colab port-forwarding) ────────────────────────
# Injecte Access-Control-Allow-Origin sur toutes les réponses
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/", methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path=""):
    return "", 204


# ─── CHEMINS ──────────────────────────────────────────────────────────────────
# Configurés depuis le notebook
DRIVE_BASE = Path(os.environ.get("DRIVE_BASE", "/content/drive/MyDrive/DRIVE_LACRIMAE"))
F02_BASE   = DRIVE_BASE / "F02_VISIO"
IN_DIR     = F02_BASE / "IN"
OUT_DIR    = F02_BASE / "OUT"
IMAGES_DIR = IN_DIR / "images"


# ─── ROUTES API ───────────────────────────────────────────────────────────────

@app.route("/api/timing")
def get_timing():
    """Retourne le timing.json complet."""
    timing_path = IN_DIR / "timing.json"
    if not timing_path.exists():
        return jsonify({"error": "timing.json introuvable"}), 404
    with open(timing_path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/images")
def get_images():
    """Liste les images disponibles dans IN/images/."""
    if not IMAGES_DIR.exists():
        return jsonify({"images": []})
    exts = {".jpg", ".jpeg", ".png"}
    images = sorted([
        f.name for f in IMAGES_DIR.iterdir()
        if f.suffix.lower() in exts
    ])
    return jsonify({"images": images, "count": len(images)})


@app.route("/api/image/<filename>")
def serve_image(filename):
    """Sert une image depuis IN/images/."""
    img_path = IMAGES_DIR / filename
    if not img_path.exists():
        return "Image introuvable", 404
    # FIX: passer Path directement (Flask ≥ 2.0), pas str()
    return send_file(img_path)


@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Retourne le creative_config.json sauvegardé (si existant).
    NOTE : la config par défaut retournée a validated_by_magos=False.
           Pour passer LAC_CUSTOS check-out, il faut obligatoirement
           avoir validé via POST /api/config depuis le viewer.
    """
    config_path = OUT_DIR / "creative_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    # Config par défaut — non validée, pour preview uniquement
    return jsonify(get_default_config())


@app.route("/api/config", methods=["POST"])
def save_config():
    """
    Sauvegarde le creative_config.json validé par le Magos.
    Body JSON attendu : objet creative_config complet.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON requis"}), 400

    # Validation minimale
    required = ["fps", "resolution", "cut_interval_frames", "font_main",
                "font_strong", "grain_overlay_opacity"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Clés manquantes : {missing}"}), 400

    data["validated_by_magos"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    config_path = OUT_DIR / "creative_config.json"

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "path": str(config_path)})


@app.route("/api/status")
def status():
    """Status général de la frégate F02."""
    timing_exists = (IN_DIR / "timing.json").exists()
    config_exists = (OUT_DIR / "creative_config.json").exists()

    nb_images = 0
    if IMAGES_DIR.exists():
        exts = {".jpg", ".jpeg", ".png"}
        nb_images = len([f for f in IMAGES_DIR.iterdir() if f.suffix.lower() in exts])

    return jsonify({
        "frigate": "F02_VISIO",
        "timing_loaded": timing_exists,
        "images_count": nb_images,
        "config_saved": config_exists,
        "ready_for_transit": timing_exists and nb_images > 0 and config_exists,
    })


@app.route("/")
def viewer():
    """Sert le viewer HTML."""
    viewer_path = Path(__file__).parent / "lac_f02_viewer.html"
    if not viewer_path.exists():
        viewer_path = Path("/content/lac_f02_viewer.html")
    # FIX: gestion d'erreur explicite si le fichier est introuvable
    if not viewer_path.exists():
        return (
            "<h1>LACRIMAE VISIO</h1>"
            "<p>Viewer HTML introuvable. Vérifiez que lac_f02_viewer.html "
            "est bien copié dans le répertoire courant ou dans /content/.</p>",
            404,
        )
    return send_file(viewer_path)


# ─── CONFIG PAR DÉFAUT ────────────────────────────────────────────────────────

def get_default_config() -> dict:
    return {
        "fps": 30,
        "resolution": {"width": 1080, "height": 1920},
        "cut_interval_frames": 7,
        "image_order": "sequential",
        "font_main": "Cinzel",
        "font_strong": "Playfair Display",
        "text_color": "#FFFFFF",
        "text_shadow": "0px 4px 12px rgba(0,0,0,0.9)",
        "letter_spacing": "0.12em",
        "grain_overlay_opacity": 0.30,
        "css_filters": "contrast(1.2) brightness(0.88) sepia(0.15)",
        "blend_mode": "screen",
        "word_animation": "fade",
        "validated_by_magos": False,
    }


# ─── LANCEMENT ────────────────────────────────────────────────────────────────

def start_server(port: int = 5000) -> None:
    """Lance le serveur Flask sur le port donné."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[VISIO] Serveur Flask démarré sur le port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_server()

