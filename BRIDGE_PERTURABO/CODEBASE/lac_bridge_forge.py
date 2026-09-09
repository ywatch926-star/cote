"""
LAC_BRIDGE_FORGE — Pont entre PERTURABO (MONDES_FORGES/CLIPPING) et LACRIMAE
=============================================================================
Mode FORGE : LACRIMAE ne réfléchit pas, il crée ce que Perturabo lui dit de créer.

L'ORACLE (bridge) est AUTONOME pour UNE chose : récupérer le pack dans le monde
forge CLIPPING de Perturabo, sans intervention du Champion. Il ne prend QUE le
production_pack_*.json du dossier EXPORT — RIEN D'AUTRE.

  PAS dans le pack → fourni par l'opérateur :
    - la VIDÉO à découper  (SHARED/IN/video_source.mp4 — directement dans IN)
    - les PNG fonds        (faits une fois pour toutes → SHARED/IN/backgrounds/)
    - le LOGO              (campagne → SHARED/IN/logos/logo.png)

Flux :
  1. RÉCUPÉRATION : liste EXPORT/ du repo PERTURABO via l'API GitHub (public par
     défaut, GITHUB_TOKEN supporté), télécharge le production_pack_*.json le
     plus récent (ou filtré par --pack-filter) → BRIDGE_PERTURABO/IN/.
  2. Contrôle (CUSTOS) : schéma du pack + cuts validés + présence de la vidéo
     locale, des fonds partagés et du logo → CONTRÔLE 1 (notre v1).
  3. Mapping pack → artefacts LACRIMAE :
       videos[].cut.start_sec/end_sec → F02_FORMAT/IN/cutlist.json
       videos[].title / viral_paragraph / on_screen_text → texts par clip
       logo_placement → session.logo (image transparente campagne)
       reference_clip_style → session (fond : blur=false → profil background)
  4. Transite : vidéo → F02/IN, TOUS les fonds partagés → public/backgrounds/
     des frégates F03+F04 + manifest.json (menu déroulant preview), logo →
     public/logo.png, codex → F03/F04 IN + public.

Le mode forge SAUTE F01 (les cuts viennent du pack, pas de vision OpenRouter).
Le mode forge UTILISE le profil F02 `background` (découpe seule — la mise en
page se fait dans la composition Remotion, fond PNG + vidéo).

Usage:
  # Oracle : le bridge va chercher le pack seul dans PERTURABO/EXPORT
  python lac_bridge_forge.py [--pack-filter SANDOVAL]
                              [--video /path/video_source.mp4]
  # Manuel : pack fourni en local
  python lac_bridge_forge.py --pack /path/EXPORT/production_pack_logo.json \
                             [--video /path/video_source.mp4]
                             [--mode logo]        # logo (défaut) | libre
                             [--dry-run]

Assets opérateur (PAS dans Perturabo) :
    - vidéo  : SHARED/IN/video_source.mp4 (directement dans IN) — ou --video,
               repli BRIDGE_PERTURABO/IN/video_source.mp4
    - fonds  : SHARED/IN/backgrounds/*.png  (une fois pour toutes)
    - logo   : SHARED/IN/logos/logo.png

Sorties :
  BRIDGE_PERTURABO/OUT/cutlist.json + OUT/codex.json + OUT/bridge_report.json
  + transits vers F02/IN, F03, F04 (public + IN)
"""

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # racine LACRIMAE
BRIDGE_BASE = ROOT / "BRIDGE_PERTURABO"
BRIDGE_IN = BRIDGE_BASE / "IN"
BRIDGE_OUT = BRIDGE_BASE / "OUT"
# Dossier partagé IN — l'opérateur dépose ici les assets qui ne sont PAS dans
# le pack Perturabo :
#   SHARED/IN/video_source.mp4  — la vidéo à découper (directement dans IN,
#                                  pas de sous-dossier videos/)
#   SHARED/IN/backgrounds/*.png — fonds (faits une fois pour toutes)
#   SHARED/IN/logos/logo.png    — logo de campagne (optionnel)
SHARED_IN_DIR = ROOT / "SHARED" / "IN"
SHARED_VIDEO_SOURCE = SHARED_IN_DIR / "video_source.mp4"
SHARED_BACKGROUNDS_DIR = SHARED_IN_DIR / "backgrounds"
SHARED_LOGOS_DIR = SHARED_IN_DIR / "logos"
LOGO_FILENAME = "logo.png"
# Méméthèque plate : SHARED/memes/meme_XXX.mp4 (voir SHARED/memes/README.md)
MEMES_DIR = ROOT / "SHARED" / "memes"
MEME_GUIDE_PATH = ROOT / "GUIDE_UTILISATION" / "04_MODE_MEME.md"

# ─── Mode MEME : personas de tweets (génération déterministe) ────────────────
MEME_PERSONAS = [
    {"name": "Chad Hunter", "handle": "@chadhunter", "avatar_color": "#1DA1F2", "verified": True},
    {"name": "Mia Foxx", "handle": "@miafoxx", "avatar_color": "#E0245E", "verified": True},
    {"name": "Jay Walker", "handle": "@jaywalker", "avatar_color": "#17BF63", "verified": False},
    {"name": "Zoe Prime", "handle": "@zoe_prime", "avatar_color": "#F45D22", "verified": True},
    {"name": "Leo Cross", "handle": "@leocross", "avatar_color": "#794BC4", "verified": False},
]
MEME_LIKES_RANGE = (800, 25000)
MEME_REPOSTS_RANGE = (50, 3000)
MEME_REPLIES_RANGE = (10, 900)

FRIGATES = {
    # dev10 : les frégates réelles sont F02_VISIO / F03_PREVIEW / F04_SIGNUM.
    # (Les noms F02_FORMAT / F04_RENDER dataient des branches pré-dev10.)
    "F02": ROOT / "F02_VISIO",
    "F03": ROOT / "F03_PREVIEW",
    "F04": ROOT / "F04_SIGNUM",
}

# Deux formats de pack acceptés :
#  A) Pack EXPORT réel (production_pack_logo.json) : pack_id, clip_source_ref,
#     videos[] (cut + title + viral_paragraph + on_screen_text), logo_placement
#  B) Pack conforme au schéma canonique (production_pack_schema.json) :
#     identite, cibles, source, angle, cut_directives, ...
PACK_KEYS_REQUIRED = [
    "identite", "cibles", "source", "angle", "cut_directives",
    "reference_style", "text_payload", "compliance", "metadata",
    "submission_checklist",
]
PACK_KEYS_LOGO = ["pack_id", "clip_source_ref", "videos"]

# ─── PERTURABO : adresse du monde forge CLIPPING (défauts) ───────────────────
PERTURABO_REPO = "kioka8877-ux/PERTURABO"
PERTURABO_EXPORT_PATH = "MONDES_FORGES/CLIPPING/EXPORT"
PERTURABO_BRANCH = "main"


def log_ok(msg): print(f"  [✓] {msg}")
def log_err(msg): print(f"  [✗] {msg}")
def log_warn(msg): print(f"  [!] {msg}")
def log_controle(msg): print(f"\n  ╔══ CONTRÔLE ══ {msg} ══╗")


def section(title):
    print(f"\n{'─' * 60}\n  {title}\n{'─' * 60}")


# ─── RÉCUPÉRATION DU PACK (mode Oracle) ──────────────────────────────────────

def github_api(url: str) -> dict:
    """GET l'API GitHub (stdlib urllib). GITHUB_TOKEN optionnel (repo privé)."""
    headers = {"User-Agent": "LACRIMAE-BRIDGE", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest: Path) -> None:
    headers = {"User-Agent": "LACRIMAE-BRIDGE"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as resp:
        dest.write_bytes(resp.read())


def fetch_pack_from_perturabo(repo=PERTURABO_REPO, export_path=PERTURABO_EXPORT_PATH,
                              branch=PERTURABO_BRANCH, pack_filter=None, mode="logo") -> Path:
    """Mode Oracle : va chercher le pack dans PERTURABO/EXPORT tout seul.

    Ne récupère QUE le production_pack_*.json — ni zip, ni vidéo, ni PNG.
    1. Liste le dossier EXPORT via l'API GitHub
    2. Choisit le production_pack_*.json : filtré par pack_filter si fourni,
       sinon le plus récent dont le nom reflète le mode du pack (ex:
       production_pack_logo.json) — repli sur le plus récent
    3. Télécharge le pack dans BRIDGE_PERTURABO/IN/

    Retourne le chemin local du pack téléchargé.
    """
    section("ORACLE — Récupération du pack depuis PERTURABO/EXPORT")
    listing = github_api(
        f"https://api.github.com/repos/{repo}/contents/{export_path}?ref={branch}")
    files = [f for f in listing if f.get("type") == "file"]

    packs = [f for f in files if f["name"].startswith("production_pack") and f["name"].endswith(".json")]
    if not packs:
        packs = [f for f in files if "production" in f["name"].lower() and f["name"].endswith(".json")]
    if not packs:
        log_err(f"Aucun production_pack_*.json dans {export_path} (repo {repo})")
        for f in files:
            print(f"    - {f['name']}")
        sys.exit(1)

    if pack_filter:
        matched = [f for f in packs if pack_filter.lower() in f["name"].lower()]
        if not matched:
            log_err(f"--pack-filter '{pack_filter}' : aucun pack correspondant."
                    f"Packs dispo : {[f['name'] for f in packs]}")
            sys.exit(1)
        packs = matched

    # Le plus récent = le dernier par ordre alphabétique (timestamp dans le nom),
    # avec préférence au pack dont le nom reflète le mode (logo par défaut)
    chosen = sorted(packs, key=lambda f: f["name"])[-1]
    mode_packs = [f for f in packs if mode.lower() in f["name"].lower()]
    if mode_packs:
        chosen = sorted(mode_packs, key=lambda f: f["name"])[-1]
    log_ok(f"Pack trouvé : {chosen['name']}")

    BRIDGE_IN.mkdir(parents=True, exist_ok=True)
    pack_dest = BRIDGE_IN / "production_pack.json"
    download_file(chosen["download_url"], pack_dest)
    log_ok(f"Pack téléchargé → {pack_dest} ({pack_dest.stat().st_size} octets)")
    log_ok("Rien d'autre n'est récupéré depuis Perturabo (vidéo + PNG = opérateur)")
    return pack_dest


# ─── CONTRÔLE 1 : validation du pack ─────────────────────────────────────────

def validate_pack(pack: dict) -> list:
    """Retourne la liste des erreurs (vide = pack OK). Accepte le pack EXPORT
    réel (format logo) OU le pack conforme au schéma canonique."""
    errors = []
    is_logo_format = all(k in pack for k in PACK_KEYS_LOGO)

    if not is_logo_format:
        # Format schéma canonique
        for key in PACK_KEYS_REQUIRED:
            if key not in pack:
                errors.append(f"pack.{key} manquant")

    videos = pack.get("videos")
    if not isinstance(videos, list) or len(videos) == 0:
        errors.append("pack.videos doit être une liste non vide")
    else:
        for v in videos:
            cut = v.get("cut") or {}
            has_timecodes = (cut.get("start_sec") is not None
                             and cut.get("end_sec") is not None)
            if "start_sec" in cut and "end_sec" in cut and has_timecodes:
                if float(cut["end_sec"]) <= float(cut["start_sec"]):
                    errors.append(f"video {v.get('angle_id', '?')} : cut invalide (end<=start)")
            elif "start_sec" not in cut or "end_sec" not in cut:
                errors.append(f"video {v.get('angle_id', '?')} : cut.start_sec/end_sec manquant")
            else:
                # Cuts proposés sans timecodes (validation Warsmith requise) :
                # accepté — le bridge génère des timecodes par défaut répartis
                # sur la durée de la vidéo fournie.
                pass
            if not v.get("title") and not v.get("on_screen_text") and not v.get("viral_paragraph"):
                errors.append(f"video {v.get('angle_id', '?')} : ni title ni on_screen_text")
    return errors


# ─── MAPPING pack → cutlist ──────────────────────────────────────────────────

def resolve_cut_timecodes(cut: dict, index: int, count: int,
                          video_duration=None) -> tuple:
    """Retourne (start_sec, end_sec) du cut, en générant des valeurs par défaut
    si les timecodes sont absents (cuts 'validation Warsmith requise') :
    répartition UNIFORME de la durée de la vidéo sur les N coupes (sinon 30s).
    Ne plante jamais sur des valeurs null."""
    start = cut.get("start_sec")
    end = cut.get("end_sec")
    if start is None or end is None:
        if video_duration:
            start = round(video_duration * index / count, 2)
            end = round(video_duration * (index + 1) / count, 2)
        else:
            start = round(index * 30.0, 2)
            end = round((index + 1) * 30.0, 2)
    return float(start), float(end)


def pack_to_cutlist(pack: dict, video_path=None, video_duration=None) -> dict:
    """Videos[].cut → cutlist.json (format F02/F01). Gère les 2 formats.

    Les cuts sans timecodes (start_sec/end_sec = null, validation Warsmith
    requise) sont répartis UNIFORMÉMENT sur la durée de la vidéo fournie
    (probe ffprobe, sinon duration_sec du pack, sinon défaut 30s/coupe)."""
    videos = pack.get("videos", [])
    source = pack.get("clip_source_ref") or {}
    if not source:
        source = (pack.get("source") or {}).get("video_url") and {
            "reference": (pack.get("source") or {}).get("video_url")
        } or {}
    if video_duration is None and video_path is not None:
        video_duration = probe_video_duration(video_path)
    if video_duration is None:
        video_duration = source.get("duration_sec")
    n = len(videos)
    sequences = []
    for i, v in enumerate(videos):
        cut = v.get("cut") or {}
        start, end = resolve_cut_timecodes(cut, i, n, video_duration)
        reason = v.get("title") or v.get("on_screen_text") or cut.get("note", "")
        sequences.append({
            "start_sec": start,
            "end_sec": end,
            "reason": f"[{v.get('angle_id', '?')}] {reason}",
        })
    return {
        "requested_sequences": len(sequences),
        "video_duration_sec": video_duration,
        "source": source.get("reference"),
        "sequences": sequences,
        "origin": "PERTURABO_FORGE",
    }


# ─── MAPPING pack → texts (par clip) ─────────────────────────────────────────

def pack_to_texts(pack: dict) -> dict:
    """Videos[] → mapping index → {title, paragraph, mode} pour F02."""
    texts_map = {}
    videos = pack.get("videos", [])
    for i, v in enumerate(videos):
        paragraph = v.get("viral_paragraph") or ""
        title = v.get("on_screen_text") or v.get("title") or ""
        # Par défaut titre seul ; titre+paragraphe si le pack fournit le paragraphe
        mode = "title+paragraph" if paragraph and title else ("title" if title else "none")
        texts_map[str(i + 1)] = {
            "title": title,
            "paragraph": paragraph,
            "mode": mode,
        }
    return texts_map


# ─── CONTRÔLE 1 : vérification des assets OPÉRATEUR ──────────────────────────

def check_assets(video_path, shared_backgrounds, logo_path) -> list:
    """Vérifie la présence des assets fournis par l'opérateur (Contrôle 1).
    Retourne les manquants."""
    missing = []
    if not video_path.exists():
        missing.append(f"VIDÉO manquante : {video_path} "
                       f"(déposée par l'opérateur dans SHARED/IN/)")
    # Fonds PNG partagés : le mode logo de Perturabo interdit le blur → fond requis
    if not shared_backgrounds:
        missing.append(f"FONDS PNG manquants : {SHARED_BACKGROUNDS_DIR} "
                       f"(déposés une fois pour toutes)")
    if logo_path is not None and not logo_path.exists():
        missing.append(f"LOGO manquant : {logo_path}")
    return missing


def probe_video_duration(video_path) -> float | None:
    """Durée de la vidéo via ffprobe (None si ffprobe indisponible)."""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1", str(video_path)],
            stderr=subprocess.DEVNULL)
        return float(out.decode().split("=")[1].strip())
    except Exception:
        return None


def check_cuts_within_duration(pack: dict, video_path) -> list:
    """Vérifie que TOUS les cuts du pack sont dans la durée de la vidéo fournie.
    Retourne les erreurs (vide = OK).

    Pourquoi : sans ce contrôle, un cut au-delà de la durée produit un clip VIDE
    à F02 (ffmpeg -ss 200 sur une vidéo de 182s) — l'opérateur découvrirait le
    problème hors porte. La garde bloque au CONTRÔLE 1 avec un message clair : la
    vidéo fournie ne correspond pas au pack (clip_source_ref)."""
    errors = []
    duration = probe_video_duration(video_path)
    if duration is None:
        log_warn("ffprobe indisponible — contrôle durée vidéo sauté")
        return errors
    for v in pack.get("videos", []):
        cut = v.get("cut") or {}
        if cut.get("start_sec") is None or cut.get("end_sec") is None:
            continue  # cuts proposés sans timecodes — générés par pack_to_cutlist
        end = float(cut.get("end_sec", 0))
        if end > duration:
            errors.append(
                f"video {v.get('angle_id', '?')} : cut {cut.get('start_sec')}-{end}s "
                f"dépasse la durée vidéo ({duration:.1f}s) — la vidéo fournie ne "
                f"correspond pas au pack (voir clip_source_ref)")
    return errors


# ─── MODE MEME : validation + mapping pack → codex ───────────────────────────

def is_meme_v2_pack(pack: dict) -> bool:
    """True pour le contrat réaction MEME V2 préparé par PERTURABO."""
    return pack.get("sub_mode") == "meme_v2" or pack.get("mode") == "meme_v2"


def is_meme_pack(pack: dict) -> bool:
    """True si le pack est en mode meme classique (contrat MEME V1)."""
    return pack.get("sub_mode") == "meme" and not is_meme_v2_pack(pack)


def ensure_release_meme_asset(meme_ref: str) -> str | None:
    """Résout un tag de Release (ex. M7/m7) en asset MP4 local normalisé."""
    if not meme_ref:
        return None
    meme_name = meme_ref if str(meme_ref).lower().endswith('.mp4') else f"{meme_ref}.mp4"
    target = MEMES_DIR / meme_name
    if target.exists():
        return meme_name
    ref = Path(str(meme_ref)).stem
    if not ref.lower().startswith('m') or not ref[1:].isdigit():
        return None
    repo = os.environ.get('GITHUB_REPOSITORY', 'kioka8877-ux/LACRIMAE')
    with tempfile.TemporaryDirectory(prefix='lacrimae-release-') as tmp:
        try:
            subprocess.run([
                'gh', 'release', 'download', ref.lower(), '--repo', repo,
                '--pattern', '*.mp4', '--dir', tmp, '--clobber',
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, 'stderr', '') or str(exc)
            print(f"  [!] Release {ref.lower()} non résolue : {detail.strip()}")
            return None
        assets = sorted(Path(tmp).glob('*.mp4'))
        if len(assets) != 1:
            print(f"  [!] Release {ref.lower()} : {len(assets)} asset(s) MP4 trouvé(s), attendu 1")
            return None
        MEMES_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(assets[0], target)
        print(f"  [✓] Tag Release {ref} → {target.name} ({assets[0].name})")
    return meme_name


def validate_meme_v2_pack(pack: dict) -> list:
    """Validation stricte du contrat MEME V2 : PERTURABO fournit tout l’éditorial."""
    errors = []
    videos = pack.get("videos")
    if not isinstance(videos, list) or not videos:
        return ["pack.videos doit être une liste non vide (mode meme_v2)"]
    for v in videos:
        angle = v.get("angle_id", "?")
        reaction = v.get("reaction_tweet") or (v.get("reaction") or {}).get("text")
        source = v.get("source_post") or {}
        screenshot = source.get("screenshot_png") or source.get("screenshot")
        if not reaction:
            errors.append(f"video {angle} : reaction_tweet manquant")
        if not screenshot:
            errors.append(f"video {angle} : source_post.screenshot_png manquant")
        if not v.get("text_emotion"):
            errors.append(f"video {angle} : text_emotion manquant")
        meme = v.get("meme")
        if not meme:
            errors.append(f"video {angle} : meme manquant")
        else:
            meme_name = ensure_release_meme_asset(str(meme))
            if not meme_name or not (MEMES_DIR / meme_name).exists():
                expected = meme if str(meme).endswith(".mp4") else f"{meme}.mp4"
                errors.append(f"video {angle} : meme '{expected}' absent et tag Release non résolu")
        dur = v.get("duration_sec")
        if dur is not None:
            try:
                dur = float(dur)
            except (TypeError, ValueError):
                errors.append(f"video {angle} : duration_sec invalide ({dur})")
                continue
            if not (3.0 <= dur <= 10.0):
                errors.append(f"video {angle} : duration_sec hors range autorisée 3-10s ({dur}s)")
    return errors


def validate_meme_pack(pack: dict) -> list:
    """Validation spécifique mode meme — retourne les erreurs (vide = OK).
    Échecs BLOQUANTS (contrat §7) :
      - meme manquant ou absent de la méméthèque SHARED/memes/
      - tweet.text ou text_emotion manquant
      - durée hors range (défaut 5-7s)
    NB : le guide 04_MODE_MEME.md est vérifié en amont par main()."""
    errors = []
    videos = pack.get("videos")
    if not isinstance(videos, list) or len(videos) == 0:
        errors.append("pack.videos doit être une liste non vide (mode meme)")
        return errors

    for v in videos:
        angle = v.get("angle_id", "?")
        meme = v.get("meme")
        if not meme:
            errors.append(f"video {angle} : meme manquant (ex 'meme_004')")
        else:
            meme_name = meme if meme.endswith(".mp4") else f"{meme}.mp4"
            if not (MEMES_DIR / meme_name).exists():
                errors.append(f"video {angle} : meme '{meme_name}' ABSENT de la "
                              f"méméthèque {MEMES_DIR}/")
        tweet = v.get("tweet") or {}
        if not tweet.get("text"):
            errors.append(f"video {angle} : tweet.text manquant")
        if not v.get("text_emotion"):
            errors.append(f"video {angle} : text_emotion manquant")
        dur = v.get("duration_sec")
        if dur is not None:
            try:
                dur = float(dur)
            except (TypeError, ValueError):
                errors.append(f"video {angle} : duration_sec invalide ({dur})")
                dur = None
            if dur is not None and not (3.0 <= dur <= 10.0):
                errors.append(f"video {angle} : duration_sec hors range "
                              f"autorisée 3-10s ({dur}s)")
    return errors


def meme_duration_sec(v: dict) -> float:
    """Durée cible d'un angle meme : duration_sec du pack (sinon range défaut 5-7s)."""
    dur = v.get("duration_sec")
    if dur is not None:
        try:
            return float(dur)
        except (TypeError, ValueError):
            pass
    return 6.0  # défaut contrat (range 5-7s)


def gen_tweet_card(pack: dict, clip_id: str) -> dict:
    """Card tweet générée par LACRIMAE (déterministe, seed = pack_id + clip_id) :
    persona (5) + likes/reposts/réponses crédibles. Aucune API externe."""
    pack_id = pack.get("pack_id") or "MEME"
    seed = int(hashlib.sha256(f"LACRIMAE-MEME-v1|{pack_id}|{clip_id}".encode("utf-8")).hexdigest(), 16)
    rnd = random.Random(seed)
    persona = MEME_PERSONAS[rnd.randrange(len(MEME_PERSONAS))]
    likes = rnd.randint(*MEME_LIKES_RANGE)
    reposts = rnd.randint(*MEME_REPOSTS_RANGE)
    replies = rnd.randint(*MEME_REPLIES_RANGE)
    # Garder la hiérarchie crédible : likes > reposts > réponses
    if reposts > likes:
        reposts = rnd.randint(MEME_REPOSTS_RANGE[0], likes)
    if replies > reposts:
        replies = rnd.randint(MEME_REPLIES_RANGE[0], max(MEME_REPLIES_RANGE[0], reposts))
    return {
        "persona": persona,
        "likes": likes,
        "reposts": reposts,
        "replies": replies,
    }


def build_meme_v2_codex(pack: dict, background_name, source_map=None, fps=30) -> dict:
    """Codex MEME V2 : aucun contenu éditorial généré, tout vient du pack."""
    source_map = source_map or {}
    clips = []
    for i, v in enumerate(pack.get("videos", [])):
        duration = meme_duration_sec(v)
        meme_name = v.get("meme")
        meme_file = meme_name if meme_name.endswith(".mp4") else f"{meme_name}.mp4"
        source = v.get("source_post") or {}
        original_screenshot = source.get("screenshot_png") or source.get("screenshot")
        clips.append({
            "id": f"clip_{i + 1:03d}",
            "angle_id": v.get("angle_id", f"A{i + 1:02d}"),
            "video": {"source": f"clip_{i + 1:03d}.mp4", "fps": fps, "total_frames": int(duration * fps), "width": 1080, "height": 1920},
            "meme": {"source": meme_file},
            "reaction_tweet": v.get("reaction_tweet") or (v.get("reaction") or {}).get("text", ""),
            "source_post": {
                "platform": source.get("platform", "social"),
                "post_url": source.get("post_url") or source.get("url", ""),
                "screenshot_png": source_map.get(original_screenshot, original_screenshot),
            },
            "text_emotion": v.get("text_emotion", ""),
            "meme_v2": {"timeline": {"reaction_start_pct": 0, "source_start_pct": 15, "emotion_start_pct": 33, "clip_start_pct": 41}},
        })
    return {
        "version": "5.0", "pipeline": "LACRIMAE_DEV", "mode": "meme", "sub_mode": "meme_v2",
        "forge": {"pack_id": pack.get("pack_id"), "siege_id": pack.get("siege_id"), "pack_mode": "meme_v2"},
        "session": {"background": {"image": background_name or None, "color": "#0a0a0a", "scale": 1.0}},
        "validated_by_magos": False, "clips": clips,
    }


def transit_meme_v2_sources(pack: dict, pack_dir: Path) -> dict:
    """Copie les captures locales fournies par PERTURABO vers public/source_posts/."""
    mapping = {}
    sources = []
    for v in pack.get("videos", []):
        src_ref = (v.get("source_post") or {}).get("screenshot_png") or (v.get("source_post") or {}).get("screenshot")
        if not src_ref or str(src_ref).startswith(("http://", "https://", "data:")):
            continue
        src = Path(src_ref)
        candidates = [src if src.is_absolute() else pack_dir / src, Path(src_ref)]
        found = next((c for c in candidates if c.exists()), None)
        if not found and "MONDES_FORGES/CLIPPING/EXPORT/" in str(src_ref):
            relative = str(src_ref).split("MONDES_FORGES/CLIPPING/EXPORT/", 1)[1].lstrip("/")
            url = "https://raw.githubusercontent.com/kioka8877-ux/PERTURABO/main/MONDES_FORGES/CLIPPING/EXPORT/" + relative
            with tempfile.NamedTemporaryFile(prefix="source-post-", suffix=Path(relative).suffix or ".png", delete=False) as tmp:
                try:
                    urllib.request.urlretrieve(url, tmp.name)
                    found = Path(tmp.name)
                    print(f"  [✓] Capture PERTURABO téléchargée : {Path(relative).name}")
                except Exception as exc:
                    print(f"  [!] Capture PERTURABO non résolue : {url} ({exc})")
        if not found:
            continue
        filename = f"source_{len(sources)+1:03d}{found.suffix.lower() or '.png'}"
        for name in ("F03", "F04"):
            dest_dir = FRIGATES[name] / "CODEBASE" / "public" / "source_posts"
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(found, dest_dir / filename)
        mapping[str(src_ref)] = f"source_posts/{filename}"
        sources.append(found)
    log_ok(f"captures MEME V2 : {len(sources)} transitées vers F03 + F04")
    return mapping


def build_meme_codex(pack: dict, background_name, fps=30) -> dict:
    """Codex v4.1 mode MEME : session (fond, logo, watermark, textes, presets)
    + clips[] (meme, tweet, text_emotion, titre, durée pack)."""
    videos = pack.get("videos", [])
    clips = []
    for i, v in enumerate(videos):
        clip_id = f"clip_{i + 1:03d}"
        duration = meme_duration_sec(v)
        tweet = (v.get("tweet") or {})
        card = gen_tweet_card(pack, clip_id)
        meme_name = v.get("meme")
        meme_file = meme_name if meme_name.endswith(".mp4") else f"{meme_name}.mp4"
        title = v.get("title")
        clips.append({
            "id": clip_id,
            "angle_id": v.get("angle_id", f"A{i + 1:02d}"),
            "video": {
                "source": f"clip_{i + 1:03d}.mp4",
                "fps": fps,
                "total_frames": int(duration * fps),
                "width": 1080,
                "height": 1920,
            },
            "meme": {
                "source": meme_file,
                # total_frames réels du meme : rempli par F02 (probe) — la
                # composition boucle net / trime selon durée pack vs réelle.
            },
            "texts": {
                "mode": "title" if title else "none",
                "title": title or "",
                "emotion": v.get("text_emotion", ""),
                "title_offset_pct": 4,
            },
            "tweet": {
                "text": tweet.get("text", ""),
                "keywords_style": tweet.get("keywords_style") or {},
                "persona": card["persona"],
                "likes": card["likes"],
                "reposts": card["reposts"],
                "replies": card["replies"],
            },
            "logo": None,  # session.logo
            "volume": 1.0,
            "brutal_cut_interval_frames": 0,
            "slowmo_start_frame": 0,
            "slowmo_speed": 1.0,
            "shake_power": 0,
        })

    codex = {
        "version": "4.1",
        "pipeline": "LACRIMAE_DEV",
        "mode": "meme",
        "sub_mode": "meme",
        "forge": {
            "pack_id": pack.get("pack_id"),
            "siege_id": pack.get("siege_id"),
            "pack_mode": pack.get("mode", "logo"),
            "campaign_id": (pack.get("identite") or {}).get("campaign_id"),
            "montage_guide_ref": pack.get("montage_guide_ref"),
        },
        "session": {
            "background": {
                "image": background_name or None,
                "color": "#0a0a0a",
                "scale": 1.0,
            },
            "logo": {
                "src": LOGO_FILENAME,
                "width_pct": 18,
                "position": "bottom_right",
                "opacity": 1.0,
            },
            "watermark": {
                "text": "@lacrimae",
                "opacity": 0.4,
                "font_size": 36,
                "position": "bottom_left",
                "color": "#FFFFFF",
            },
            "texts_style": {
                "font": "Impact, Arial Black, sans-serif",
                "size_title": 64,
                "size_paragraph": 40,
                "color": "#FFFFFF",
                "stroke_color": "#000000",
                "stroke_width": 4,
                "shadow": "2px 4px 8px rgba(0,0,0,0.9)",
                "glow_intensity": 0,
                "letter_spacing": "0em",
            },
            "presets": {
                "color_preset": "punchy",
                "color_css_filter": "contrast(1.3) saturate(1.5) brightness(1.1)",
                "enhance_4k": False,
                "sharpening": 0,
                "denoising": 0,
                "vignette": 0.25,
                "grain_intensity": 0.15,
            },
        },
        "validated_by_magos": False,
        "clips": clips,
    }
    return codex


def transit_memes_to_f02():
    """Tous les memes partagés → F02/IN/memes/ (staging F02 sans découpe)."""
    f02_in = FRIGATES["F02"] / "IN" / "memes"
    f02_in.mkdir(parents=True, exist_ok=True)
    memes = sorted(MEMES_DIR.glob("*.mp4")) if MEMES_DIR.exists() else []
    for meme in memes:
        shutil.copy2(meme, f02_in / meme.name)
    log_ok(f"F02/IN/memes : {len(memes)} meme(s) transité(s)")
    return memes


def transit_memes_to_preview_render():
    """Tous les memes partagés → public/memes/ des F03+F04 (parcours méméthèque
    + rendu) + manifest.json (menu déroulant de la preview)."""
    memes = sorted(MEMES_DIR.glob("*.mp4")) if MEMES_DIR.exists() else []
    for name, frig in FRIGATES.items():
        if name == "F02":
            continue
        meme_dir = frig / "CODEBASE" / "public" / "memes"
        meme_dir.mkdir(parents=True, exist_ok=True)
        for meme in memes:
            shutil.copy2(meme, meme_dir / meme.name)
        manifest = sorted(meme.name for meme in memes)
        (meme_dir / "manifest.json").write_text(
            json.dumps({"files": manifest}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        log_ok(f"{frig.name} : {len(memes)} meme(s) transité(s) → public/memes/")
    return memes


# ─── TRANSITS ────────────────────────────────────────────────────────────────

def transit_to_f02(video_path, cutlist_path):
    f02 = FRIGATES["F02"]
    f02_in = f02 / "IN"
    f02_in.mkdir(parents=True, exist_ok=True)
    dest_video = f02_in / "video_source.mp4"
    # GHA : la vidéo est déjà téléchargée directement dans F02/IN (--video
    # F02_FORMAT/IN/video_source.mp4) — copie = no-op, pas d'erreur.
    if video_path.resolve() != dest_video.resolve():
        shutil.copy2(video_path, dest_video)
    shutil.copy2(cutlist_path, f02_in / "cutlist.json")
    log_ok(f"F02/IN : video_source.mp4 + cutlist.json")


def transit_backgrounds_to_preview_render():
    """TOUS les fonds partagés → public/backgrounds/ des F03+F04 + manifest.json.
    (Le menu déroulant de la preview se nourrit de ce manifest.json.)"""
    manifest = []
    backgrounds = sorted(SHARED_BACKGROUNDS_DIR.glob("*.png")) if SHARED_BACKGROUNDS_DIR.exists() else []
    for name, frig in FRIGATES.items():
        if name == "F02":
            continue
        bg_dir = frig / "CODEBASE" / "public" / "backgrounds"
        bg_dir.mkdir(parents=True, exist_ok=True)
        for bg in backgrounds:
            shutil.copy2(bg, bg_dir / bg.name)
        manifest = sorted(bg.name for bg in backgrounds)
        (bg_dir / "manifest.json").write_text(
            json.dumps({"files": manifest}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        log_ok(f"{frig.name} : {len(manifest)} fond(s) transité(s) + manifest.json")
    return manifest


def transit_logo(logo_path):
    if not logo_path or not logo_path.exists():
        return
    for name, frig in FRIGATES.items():
        if name == "F02":
            continue
        shutil.copy2(logo_path, frig / "CODEBASE" / "public" / LOGO_FILENAME)
    log_ok("logo.png transité vers F03 + F04 (public/)")


def transit_codex(codex_path):
    """codex.json forge → F03/IN + F03/public + F04/IN + F04/public."""
    for name in ("F03", "F04"):
        frig = FRIGATES[name]
        for dst in (frig / "IN", frig / "CODEBASE" / "public"):
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(codex_path, dst / "codex.json")
    log_ok("codex.json forge transité vers F03 + F04")


# ─── CODEX FORGE (v4.0, session + clips) ─────────────────────────────────────

def build_forge_codex(pack: dict, texts_map: dict, background_name,
                      video_duration=None, fps=30) -> dict:
    videos = pack.get("videos", [])
    n = len(videos)
    clips = []
    for i, v in enumerate(videos):
        cut = v.get("cut") or {}
        _, end = resolve_cut_timecodes(cut, i, n, video_duration)
        duration_sec = cut.get("duration_sec")
        if duration_sec is None:
            start, end = resolve_cut_timecodes(cut, i, n, video_duration)
            duration_sec = end - start
        duration = float(duration_sec)
        t = texts_map.get(str(i + 1), {})
        clips.append({
            "id": f"clip_{i + 1:03d}",
            "angle_id": v.get("angle_id", f"A{i + 1:02d}"),
            "video": {
                "source": f"clip_{i + 1:03d}.mp4",
                "fps": fps,
                "total_frames": int(duration * fps),
                "width": 1080,
                "height": 1920,
            },
            "texts": {
                "mode": t.get("mode", "title"),
                "title": t.get("title", ""),
                "paragraph": t.get("paragraph", ""),
                "title_offset_pct": 8,
                "paragraph_offset_pct": 8,
            },
            "text_overlays": [
                {
                    "id": "title_00",
                    "content": t.get("title", ""),
                    "start_frame": 0,
                    "end_frame": int(duration * fps),
                    "animation": "fade_in",
                    "font": "Impact, Arial Black, sans-serif",
                    "size": 96,
                    "color": "#FFFFFF",
                    "stroke_color": "#000000",
                    "stroke_width": 4,
                    "shadow": "2px 4px 8px rgba(0,0,0,0.9)",
                    "position": "top",
                    "letter_spacing": "0em",
                    "glow_intensity": 0,
                    "depth_3d": 0,
                }
            ],
            "zoom_keyframes": [],
            "logo": None,  # session.logo
            "brutal_cut_interval_frames": 0,  # forge : pas de coup brutal imposé
            "volume": 1.0,
            "slowmo_start_frame": 0,
            "slowmo_speed": 1.0,
            "shake_power": 0,
        })

    codex = {
        "version": "4.0",
        "pipeline": "LACRIMAE_DEV",
        "mode": "forge",
        "forge": {
            "pack_id": pack.get("pack_id"),
            "siege_id": pack.get("siege_id"),
            "pack_mode": pack.get("mode", "logo"),
            "campaign_id": (pack.get("identite") or {}).get("campaign_id"),
        },
        "session": {
            "background": {
                "image": background_name,  # fond partagé choisi (défaut = 1er trié)
                "color": "#0a0a0a",
                "scale": 1.0,
            },
            "logo": {
                "src": LOGO_FILENAME,
                "width_pct": 20,
                "position": "bottom_left",
                "opacity": 1.0,
            },
            "texts_style": {
                "font": "Impact, Arial Black, sans-serif",
                "size_title": 96,
                "size_paragraph": 44,
                "color": "#FFFFFF",
                "stroke_color": "#000000",
                "stroke_width": 4,
                "shadow": "2px 4px 8px rgba(0,0,0,0.9)",
                "glow_intensity": 0,
                "letter_spacing": "0em",
            },
            "presets": {
                "color_preset": "punchy",
                "color_css_filter": "contrast(1.3) saturate(1.5) brightness(1.1)",
                "enhance_4k": False,
                "sharpening": 0,
                "denoising": 0,
                "vignette": 0.25,
                "grain_intensity": 0.15,
            },
        },
        "validated_by_magos": False,
        "clips": clips,
    }
    return codex


# ─── MODE PUR — bras armé (fetch + conversion manifeste) ───────────────────

def run_pur_mode(args):
    """Mode PUR : récupère le pack PUR depuis EXPORT PERTURABO, le valide (G0),
    puis convertit en pur_manifest.json (dev10.pur.v1) via bridgeClipper.js.
    Le téléchargement du segment VOD reste à F00-PUR (f00_pur.py) — le bridge
    ne prend QUE le JSON, jamais la vidéo (doctrine mode FORGE)."""
    section("LAC_BRIDGE_FORGE — MODE PUR (bras armé PERTURABO)")
    pack_path = Path(args.pack) if args.pack else fetch_pack_from_perturabo(
        pack_filter=args.pack_filter, mode="pur")
    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    ok, errors = validate_pur_pack(pack)
    if not ok:
        for e in errors:
            log_err(f"G0 PACK : {e}")
        print("\n  ══ MODE PUR : ✗ ÉCHOUÉ — pack invalide ══")
        sys.exit(1)
    mi = pack["montage_instructions"]
    segment = mi.get("segment") or pack.get("source") or {}
    log_ok(f"Pack PUR valide : {pack.get('pack_id', '?')} | "
           f"angle {pack.get('identite', {}).get('angle_id', '?')} | "
           f"segment {segment.get('start_sec')}s → {segment.get('end_sec')}s")

    if args.dry_run:
        print(f"\n[DRY-RUN] Mode PUR : {pack_path} → BRIDGE_PERTURABO/OUT/pur_manifest.json "
              f"(canvas {args.canvas}). Aucun fichier écrit.")
        return

    BRIDGE_OUT.mkdir(parents=True, exist_ok=True)
    manifest = convert_pur_pack_to_manifest(pack, canvas=args.canvas)
    manifest_path = BRIDGE_OUT / "pur_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log_ok(f"pur_manifest.json écrit : {manifest_path} ({manifest['total_frames']} frames)")

    # Transit vers F03/F04 public (preview + rendu consomment le même fichier)
    transit_pur_manifest(manifest_path)

    print()
    print("═" * 52)
    print(" BRIDGE FORGE (MODE PUR) — MISSION ACCOMPLIE")
    print(f"  Pack      : {pack.get('pack_id', '?')}")
    print(f"  Manifeste : {manifest_path} → F03/F04 public")
    print(f"  Prochain  : F00-PUR (f00_pur.py) télécharge le segment VOD,")
    print("              puis workflow dev10_pur_render → MP4.")
    print("═" * 52)


def validate_pur_pack(pack: dict) -> tuple[bool, list[str]]:
    """G0 PUR côté bridge — mêmes critères que F00_INGEST/CODEBASE/f00_pur.py."""
    errors = []
    if not isinstance(pack, dict):
        return False, ["pack illisible"]
    if pack.get("mode") != "pur":
        errors.append(f"mode={pack.get('mode')!r}, attendu 'pur'")
    source = pack.get("source") or {}
    mi = pack.get("montage_instructions") or {}
    segment = mi.get("segment") or source
    if not (segment.get("source_url") or source.get("vod_url")):
        errors.append("vod_url absente")
    if not mi:
        errors.append("montage_instructions absente")
    start = segment.get("start_sec", source.get("start_sec"))
    end = segment.get("end_sec", source.get("end_sec"))
    if start is None or end is None or float(end) <= float(start):
        errors.append("segment invalide (end <= start)")
    return len(errors) == 0, errors


def convert_pur_pack_to_manifest(pack: dict, canvas: str = "9:16") -> dict:
    """Convertit le pack via bridgeClipper.js (parsePurPack) — même code que la CI."""
    import subprocess
    root = Path(__file__).resolve().parent.parent.parent
    script = root / "tools" / "convert_pur_pack.mjs"
    if not script.is_file():
        log_err(f"Script de conversion absent : {script}")
        sys.exit(1)
    tmp_pack = BRIDGE_OUT / "pur_pack_in.json"
    tmp_pack.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    out = BRIDGE_OUT / "pur_manifest.json"
    cmd = ["node", str(script), "--pack", str(tmp_pack), "--out", str(out), "--canvas", canvas]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log_err(f"Conversion bridgeClipper échouée :\n{result.stderr}")
        sys.exit(1)
    print(result.stdout.strip())
    return json.loads(out.read_text(encoding="utf-8"))


def transit_pur_manifest(manifest_path: Path) -> None:
    """Copie pur_manifest.json + pur_pack_in.json dans public/ de F03 et F04."""
    for frigate_public in (FRIGATES["F03"] / "CODEBASE" / "public",
                           ROOT / "F03_PICTOR" / "CODEBASE" / "public"):
        if frigate_public.parent.exists():
            frigate_public.mkdir(parents=True, exist_ok=True)
            shutil.copy2(manifest_path, frigate_public / "pur_manifest.json")
            log_ok(f"Transit → {frigate_public / 'pur_manifest.json'}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LAC_BRIDGE_FORGE — Pont PERTURABO → LACRIMAE")
    parser.add_argument("--pack", default=None,
                        help="Chemin du production_pack.json — SI ABSENT, le bridge va le "
                             "chercher seul dans PERTURABO/EXPORT (mode Oracle)")
    parser.add_argument("--pack-filter", default=None,
                        help="Filtre du pack à auto-récupérer (substring du nom, ex: SANDOVAL, pur_A01)")
    parser.add_argument("--video", help="Vidéo source locale (déposée par l'opérateur)")
    parser.add_argument("--mode", default="logo", choices=["logo", "libre"],
                        help="Mode du pack (défaut logo)")
    parser.add_argument("--pur", action="store_true",
                        help="MODE PUR : fetch pack production_pack_pur_*.json → BRIDGE_PERTURABO/IN/ "
                             "puis conversion en pur_manifest.json (dev10.pur.v1). Rien d'autre.")
    parser.add_argument("--canvas", default="9:16", choices=["9:16", "16:9", "1:1"],
                        help="Canvas du manifeste PUR (défaut 9:16)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche le plan sans écrire")
    args = parser.parse_args()

    # ════════════════ MODE PUR (bras armé) ════════════════
    if args.pur:
        run_pur_mode(args)
        return

    section("LAC_BRIDGE_FORGE — import du pack Perturabo")
    log_controle("CONTRÔLE 1 — VALIDATION DU PACK")

    # 0. Pack : local fourni OU auto-récupéré depuis PERTURABO/EXPORT (Oracle)
    if args.pack:
        pack_path = Path(args.pack)
        if not pack_path.exists():
            log_err(f"Pack introuvable : {pack_path}")
            sys.exit(1)
        log_ok(f"Pack local : {pack_path}")
    else:
        pack_path = fetch_pack_from_perturabo(pack_filter=args.pack_filter,
                                              mode=args.mode)
        log_ok(f"Pack auto-récupéré : {pack_path}")

    pack = json.loads(pack_path.read_text(encoding="utf-8"))

    # ════════════════ MODE MEME V2 (reaction + capture source) ════════════════
    if is_meme_v2_pack(pack):
        if not MEME_GUIDE_PATH.exists():
            log_err(f"Guide mode MEME absent : {MEME_GUIDE_PATH}")
            sys.exit(1)
        errors = validate_meme_v2_pack(pack)
        if errors:
            for e in errors:
                log_err(e)
            print("\n  ══ CONTRÔLE 1 : ✗ ÉCHOUÉ — pack meme_v2 invalide ══")
            sys.exit(1)
        shared_backgrounds = sorted(SHARED_BACKGROUNDS_DIR.glob("*.png")) if SHARED_BACKGROUNDS_DIR.exists() else []
        background_name = shared_backgrounds[0].name if shared_backgrounds else None
        if args.dry_run:
            print(f"\n[DRY-RUN] Plan meme_v2 : {len(pack.get('videos', []))} angle(s), captures source obligatoires")
            sys.exit(0)
        BRIDGE_OUT.mkdir(parents=True, exist_ok=True)
        source_map = transit_meme_v2_sources(pack, pack_path.parent)
        codex = build_meme_v2_codex(pack, background_name, source_map)
        codex_path = BRIDGE_OUT / "codex.json"
        codex_path.write_text(json.dumps(codex, ensure_ascii=False, indent=2), encoding="utf-8")
        transit_memes_to_f02()
        transit_memes_to_preview_render()
        transit_backgrounds_to_preview_render()
        transit_codex(codex_path)
        f02_in = FRIGATES["F02"] / "IN"
        f02_in.mkdir(parents=True, exist_ok=True)
        shutil.copy2(codex_path, f02_in / "codex.json")
        print("\n  ══ BRIDGE FORGE (MODE MEME V2) — MISSION ACCOMPLIE ══")
        print(f"  Angles : {len(codex['clips'])} | captures : {len(source_map)}")
        sys.exit(0)

    # ════════════════ MODE MEME (sub_mode: meme) ════════════════
    # Aucune découpe : les memes sont déjà coupés dans la méméthèque
    # (SHARED/memes/), le pack nomme explicitement le meme de chaque angle.
    # F02 stage simplement (copie meme → clip_00X.mp4), pas de vidéo source.
    if is_meme_pack(pack):
        if not MEME_GUIDE_PATH.exists():
            log_err(f"Guide mode MEME absent : {MEME_GUIDE_PATH}")
            log_err("Un pack sub_mode: meme exige le contrat 04_MODE_MEME.md "
                    "(échec bloquant).")
            print("\n  ══ CONTRÔLE 1 : ✗ ÉCHOUÉ — mode meme sans contrat ══")
            sys.exit(1)
        log_ok(f"Contrat mode MEME présent : {MEME_GUIDE_PATH.name}")

        meme_errors = validate_meme_pack(pack)
        if meme_errors:
            for e in meme_errors:
                log_err(e)
            print("\n  ══ CONTRÔLE 1 : ✗ ÉCHOUÉ — pack meme invalide ══")
            sys.exit(1)
        log_ok(f"Pack meme valide : {pack.get('pack_id', '?')} | "
               f"{len(pack.get('videos', []))} angle(s)")

        shared_backgrounds = sorted(SHARED_BACKGROUNDS_DIR.glob("*.png")) if SHARED_BACKGROUNDS_DIR.exists() else []
        logo_path = SHARED_LOGOS_DIR / LOGO_FILENAME
        if not logo_path.exists():
            logo_path = None
        background_name = shared_backgrounds[0].name if shared_backgrounds else None

        if args.dry_run:
            print("\n[DRY-RUN] Plan meme :")
            print(f"  pack     : {pack.get('pack_id', '?')} (sub_mode meme)")
            print(f"  memes    : {len(pack.get('videos', []))} (méméthèque SHARED/memes/)")
            print(f"  fonds    : {len(shared_backgrounds)} PNG → preview + rendu"
                  + ("" if background_name else "  (aucun — couleur unie)"))
            print("  Aucun fichier écrit.")
            sys.exit(0)

        # Mapping pack → codex meme v4.1 (session + clips)
        BRIDGE_OUT.mkdir(parents=True, exist_ok=True)
        codex = build_meme_codex(pack, background_name)
        codex_path = BRIDGE_OUT / "codex.json"
        codex_path.write_text(json.dumps(codex, ensure_ascii=False, indent=2), encoding="utf-8")
        log_ok(f"codex meme v4.1 écrit : {codex_path} ({len(codex['clips'])} clip(s))")

        # Transits : memes → F02/IN + F03/F04 public, fonds, logo, codex
        transit_memes_to_f02()
        transit_memes_to_preview_render()
        transit_backgrounds_to_preview_render()
        transit_logo(logo_path)
        transit_codex(codex_path)
        # F02 (profil meme) lit le codex bridge pour le staging (IN/codex.json)
        f02_in = FRIGATES["F02"] / "IN"
        f02_in.mkdir(parents=True, exist_ok=True)
        shutil.copy2(codex_path, f02_in / "codex.json")
        log_ok(f"F02/IN : codex.json meme transité (staging)")

        report = {
            "pack_id": pack.get("pack_id"),
            "mode": pack.get("mode"),
            "sub_mode": "meme",
            "videos_count": len(pack.get("videos", [])),
            "controle1": "validated",
            "profile_f02": "meme",
            "background": background_name,
            "backgrounds_available": [b.name for b in shared_backgrounds],
            "f01_skipped": True,
            "pack_fetched": not args.pack,
            "source_video": None,
            "clips": [{"angle_id": v.get("angle_id"),
                       "meme": v.get("meme"),
                       "duration_sec": meme_duration_sec(v)} for v in pack.get("videos", [])],
        }
        (BRIDGE_OUT / "bridge_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print()
        print("═" * 52)
        print(" BRIDGE FORGE (MODE MEME) — MISSION ACCOMPLIE")
        print(f"  Pack     : {pack.get('pack_id', '?')} (récupéré par l'Oracle)")
        print(f"  Angles   : {len(codex['clips'])} (memes de la méméthèque)")
        print(f"  F01      : SAUTÉE — aucune découpe (memes prêts)")
        print(f"  Prochain : LAC_RUN.py run (F02 meme → preview F03)")
        print("═" * 52)
        sys.exit(0)

    # 1. Validation schéma + cuts (mode standard, PAS meme)
    errors = validate_pack(pack)
    if errors:
        for e in errors:
            log_err(e)
        print("\n  ══ CONTRÔLE 1 : ✗ ÉCHOUÉ — corriger le pack ══")
        sys.exit(1)
    log_ok(f"Pack valide : {pack.get('pack_id', '?')} | mode={pack.get('mode', '?')} | "
           f"{len(pack.get('videos', []))} vidéo(s)")

    # 2. Assets OPÉRATEUR (jamais dans Perturabo) :
    #    - vidéo  : SHARED/IN/video_source.mp4 (directement dans IN) — ou
    #               --video / repli BRIDGE_PERTURABO/IN/video_source.mp4
    #    - fonds  : SHARED/IN/backgrounds/*.png  (une fois pour toutes)
    #    - logo   : SHARED/IN/logos/logo.png
    if args.video:
        video_path = Path(args.video)
    elif SHARED_VIDEO_SOURCE.exists():
        video_path = SHARED_VIDEO_SOURCE
    else:
        video_path = BRIDGE_IN / "video_source.mp4"
    shared_backgrounds = sorted(SHARED_BACKGROUNDS_DIR.glob("*.png")) if SHARED_BACKGROUNDS_DIR.exists() else []
    logo_path = SHARED_LOGOS_DIR / LOGO_FILENAME
    if not logo_path.exists():
        logo_path = None

    missing = check_assets(video_path, shared_backgrounds, logo_path)
    if missing:
        for m in missing:
            log_err(m)
        print("\n  ══ CONTRÔLE 1 : ✗ ÉCHOUÉ — assets opérateur manquants ══")
        print("  Le bridge ne prend QUE le pack depuis Perturabo. Fournis :")
        print(f"    - vidéo → {SHARED_VIDEO_SOURCE} (directement dans SHARED/IN)")
        print(f"    - fonds → {SHARED_BACKGROUNDS_DIR}/ (PNG, une fois pour toutes)")
        print(f"    - logo  → {SHARED_LOGOS_DIR / LOGO_FILENAME} (optionnel)")
        sys.exit(1)

    # Garde durée : TOUS les cuts du pack doivent être dans la vidéo fournie.
    # (Sinon F02 produirait des clips vides — l'opérateur n'agit qu'aux portes.)
    cut_errors = check_cuts_within_duration(pack, video_path)
    if cut_errors:
        for e in cut_errors:
            log_err(e)
        print("\n  ══ CONTRÔLE 1 : ✗ ÉCHOUÉ — vidéo incompatible avec les cuts du pack ══")
        print("  Le pack référence une source précise (clip_source_ref) — la vidéo")
        print("  fournie doit la couvrir intégralement. Remplace-la dans la release :")
        print("    sh _tools/lac_release_video.sh <bonne_video.mp4> [tag]")
        sys.exit(1)
    background_name = shared_backgrounds[0].name  # défaut = 1er fond trié
    log_ok(f"Assets opérateur : vidéo ✓ | {len(shared_backgrounds)} fond(s) "
           f"(défaut {background_name}) ✓ | logo {'✓' if logo_path else '— (sans logo)'}")

    print("\n  ══ CONTRÔLE 1 : ✓ VALIDÉ — pack + assets prêts ══")

    if args.dry_run:
        print("\n[DRY-RUN] Plan :")
        print(f"  pack     : {pack.get('pack_id', '?')} (mode {pack.get('mode', '?')})")
        print(f"  cutlist  : {len(pack.get('videos', []))} séquences (cuts perturabo_validated)")
        print(f"  profil F02 : background (découpe seule, pas de blur — mode logo)")
        print(f"  textes   : {len(pack.get('videos', []))} clips (title/paragraph du pack)")
        print(f"  fonds    : {len(shared_backgrounds)} PNG partagés → preview + rendu")
        print("  Aucun fichier écrit.")
        sys.exit(0)

    # 3. Mapping pack → cutlist + texts
    BRIDGE_OUT.mkdir(parents=True, exist_ok=True)
    cutlist = pack_to_cutlist(pack, video_path=video_path)
    cutlist_path = BRIDGE_OUT / "cutlist.json"
    cutlist_path.write_text(json.dumps(cutlist, ensure_ascii=False, indent=2), encoding="utf-8")
    log_ok(f"cutlist forge écrit : {cutlist_path}")

    texts_map = pack_to_texts(pack)

    # 4. Codex forge v4.0 (session + clips)
    codex = build_forge_codex(pack, texts_map, background_name,
                              video_duration=cutlist.get("video_duration_sec"))
    codex_path = BRIDGE_OUT / "codex.json"
    codex_path.write_text(json.dumps(codex, ensure_ascii=False, indent=2), encoding="utf-8")
    log_ok(f"codex forge v4.0 écrit : {codex_path} ({len(codex['clips'])} clip(s))")

    # 5. Transits
    transit_to_f02(video_path, cutlist_path)
    transit_backgrounds_to_preview_render()
    transit_logo(logo_path)
    transit_codex(codex_path)

    # 6. Rapport bridge
    source = pack.get("clip_source_ref") or {}
    report = {
        "pack_id": pack.get("pack_id"),
        "mode": pack.get("mode"),
        "videos_count": len(pack.get("videos", [])),
        "controle1": "validated",
        "profile_f02": "background",
        "background": background_name,
        "backgrounds_available": [b.name for b in shared_backgrounds],
        "f01_skipped": True,
        "pack_fetched": not args.pack,  # True si auto-récupéré depuis PERTURABO
        "source_video": source.get("reference"),
        "source_type": source.get("source_type"),
        "video_local": str(video_path),
        "clips": [{"angle_id": v.get("angle_id"), "title": v.get("title"),
                   "cut": v.get("cut")} for v in pack.get("videos", [])],
    }
    (BRIDGE_OUT / "bridge_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("═" * 52)
    print(" BRIDGE FORGE — MISSION ACCOMPLIE")
    print(f"  Pack     : {pack.get('pack_id', '?')} (récupéré par l'Oracle)")
    print(f"  Mode     : {pack.get('mode', '?')}")
    print(f"  Vidéos   : {len(codex['clips'])}")
    print(f"  F01      : SAUTÉE (cuts du pack)")
    print(f"  Prochain : LAC_RUN.py run (F02 profile background → preview F03)")
    print("═" * 52)


if __name__ == "__main__":
    main()
