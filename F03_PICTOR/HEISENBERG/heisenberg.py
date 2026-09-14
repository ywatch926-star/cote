#!/usr/bin/env python3
"""HEISENBERG — sous-frégate Caviar du bras armé (embarquée dans F03_PICTOR).

Mission unique : servir la frégate. Elle reçoit les vidéos FINIES produites par
F03_PICTOR (validées par le gate qui suit F03), les analyse, et émet un
caviar_manifest.json PAR vidéo — le JSON que PERTURABO embarque dans le pack
et que le bras armé transformera en clip caviar au rendu.

Architecture (tout vit ICI, isolé — rien d'autre n'est modifié) :
  HEISENBERG/
  ├── heisenberg.py        ← ce moteur (aucune décision créative)
  ├── caviar_budget.json   ← Budget d'Attention (source de vérité unique)
  ├── BROLL/
  │   ├── registry.json    ← registre NUMÉROTÉ (PERTURABO ne voit jamais les fichiers)
  │   ├── FILES/           ← les .mp4/.png réels (jamais commités)
  │   └── candidates/      ← propositions d'ajout (une fiche = un numéro candidat)
  ├── IN/                  ← vidéos reçues de F03_PICTOR (input)
  ├── OUT/                 ← caviar_manifest_<angle>.json émis (output)
  └── LEDGER/              ← manifest_ledger.json + gate_history.json (ARCHIVUM-friendly)

Doctrine (spec CAVIAR §4) : PERTURABO = le OÙ/QUOI · LACRIMAE = le COMMENT ·
Warsmith tranche. Heisenberg ANALYSE et PROPOSE ; elle n'écrit pas l'accroche,
elle ne choisit pas le segment, elle ne décide pas du style.

Usage :
  python3 heisenberg.py --manifest OUT/pur_A01_finale.mp4                 # une vidéo
  python3 heisenberg.py --batch IN/                                      # toutes les IN/
  python3 heisenberg.py --manifest ... --emit-pack-chunk                 # chunk PERTURABO
  python3 heisenberg.py --broll "met le numéro 1" --at 8.5               # résolution d'un numéro
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HEISENBERG_ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = "dev10.caviar.v1"

# Le Budget d'Attention est ingéré depuis caviar_budget.json — UNE source de
# vérité partagée avec PERTURABO (pas de constante dupliquée dans le code).
_budget_cache: dict | None = None


def load_budget() -> dict:
    global _budget_cache
    if _budget_cache is None:
        path = HEISENBERG_ROOT / "caviar_budget.json"
        _budget_cache = json.loads(path.read_text(encoding="utf-8"))
    return _budget_cache


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    print(msg, flush=True)


# ═══════════════════════════════════════════════════════════════════
# ANALYSE — réutilisation du Directeur Caviar (F00_INGEST, zéro doublon)
# ═══════════════════════════════════════════════════════════════════

_CODEBASE_F00 = Path(__file__).resolve().parents[2] / "F00_INGEST" / "CODEBASE"


def _director():
    """Importe le module caviar (Directeur) — analyse advisory éprouvée."""
    if str(_CODEBASE_F00) not in sys.path:
        sys.path.insert(0, str(_CODEBASE_F00))
    import caviar  # noqa: E402

    return caviar


def probe(path: Path) -> dict:
    """ffprobe minimal — codec, dimensions, durée, piste audio."""
    data = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_name,codec_type,width,height:format=duration",
         "-of", "json", str(path)], text=True))
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "codec": video.get("codec_name") if video else None,
        "width": int(video.get("width") or 0) if video else 0,
        "height": int(video.get("height") or 0) if video else 0,
        "duration_sec": round(float(data.get("format", {}).get("duration") or 0), 3),
        "has_audio": audio is not None,
    }


# ═══════════════════════════════════════════════════════════════════
# BUDGET D'ATTENTION — la frégate dépense AVANT d'écrire
# ═══════════════════════════════════════════════════════════════════

def compute_budget(narrative: dict, silences_count: int, duration_sec: float) -> dict:
    """Calcule la dépense du manifeste et le verdict de saturation.

    Règles de survie (note du Warsmith) :
      - dépense totale ≤ 55 u sur 100 → le reste = respiration
      - > 8 silences à trimmer → REFUS d'émettre (« segment mauvais »)
    """
    b = load_budget()["events"]
    counts = {
        "broll": len(narrative.get("broll") or []),
        "smash": len(narrative.get("is_climax") or []),
        "punchin": len(narrative.get("zooms") or []),
        "jumpcut": silences_count,
    }
    spend = (counts["broll"] * b["broll"]["cost_units"]
             + counts["smash"] * b["smash"]["cost_units"]
             + counts["punchin"] * b["punchin"]["cost_units"]
             + counts["jumpcut"] * b["jumpcut"]["cost_units"])
    verdict = {
        "total_units": load_budget()["total_budget_units"],
        "spend_units": spend,
        "breathing_units": load_budget()["total_budget_units"] - spend,
        "source_ratio_target": load_budget()["breathing"]["min_source_ratio"],
        "caps": {
            "broll": {"count": counts["broll"], "max": b["broll"]["max_per_clip"],
                      "ok": counts["broll"] <= b["broll"]["max_per_clip"]},
            "smash": {"count": counts["smash"], "max": b["smash"]["max_per_clip"],
                      "ok": counts["smash"] <= b["smash"]["max_per_clip"]},
            "punchin": {"count": counts["punchin"], "max": b["punchin"]["max_per_clip"],
                        "ok": counts["punchin"] <= b["punchin"]["max_per_clip"]},
            "jumpcut": {"count": counts["jumpcut"], "max": b["jumpcut"]["max_per_clip"],
                        "ok": counts["jumpcut"] <= b["jumpcut"]["max_per_clip"]},
        },
        "spend_ok": spend <= load_budget()["max_spend_units"],
    }
    return verdict


# ═══════════════════════════════════════════════════════════════════
# B-ROLL NUMÉROTÉ — PERTURABO donne un numéro, le bras armé connaît le fichier
# ═══════════════════════════════════════════════════════════════════

def load_registry() -> dict:
    return json.loads((HEISENBERG_ROOT / "BROLL" / "registry.json").read_text(encoding="utf-8"))


def resolve_broll_number(number: int) -> dict:
    """'met le numéro 1' → la fiche complète (fichier, flash, SFX).

    C'est la parade demandée par le Warsmith : PERTURABO n'a JAMAIS accès aux
    fichiers B-roll. Il écrit l'émotion à illustrer + le numéro ; Heisenberg
    seule fait le lien numéro → fichier (et pose flash d'entrée + SFX couplé).
    """
    reg = load_registry()
    clip = (reg.get("clips") or {}).get(str(number))
    if clip is None:
        available = ", ".join(sorted(reg.get("clips", {}).keys(), key=str)) or "aucun"
        raise KeyError(f"B-roll numéro {number} inconnu (disponibles : {available})")
    return {
        "broll_number": int(number),
        "asset_ref": f"broll#{number}",   # référence neutre — jamais le chemin brut
        "label": clip.get("label"),
        "emotions": clip.get("emotions") or [],
        "entry_flash": bool(clip.get("entry_flash", True)),
        "sfx": clip.get("sfx") or "impact",
        "duration_frames_max": clip.get("duration_frames_max", 45),
    }


def suggest_broll_by_emotion(emotion: str) -> list[int]:
    """PERTURABO décrit l'émotion → numéros candidats (il tranche ensuite)."""
    emo = (emotion or "").strip().lower()
    out: list[int] = []
    for num, clip in (load_registry().get("clips") or {}).items():
        emotions = [e.lower() for e in (clip.get("emotions") or [])]
        if emo and any(emo in e or e in emo for e in emotions):
            out.append(int(num))
    return out


def parse_broll_order(order: str) -> list[int]:
    """'met le numéro 1' / 'numeros 1 et 3' → [1] / [1, 3]."""
    return [int(n) for n in re.findall(r"\d+", order or "")]


# ═══════════════════════════════════════════════════════════════════
# ÉMISSION DU MANIFESTE CAVIAR — PROPOSITIONS, jamais appliquées d'office
# ═══════════════════════════════════════════════════════════════════

def _proposals_from_analysis(analysis: dict, duration: float,
                             with_whisper: bool) -> dict:
    """Traduit l'analyse du Directeur en propositions Caviar (champs pack v2)."""
    budget = load_budget()
    silences = analysis.get("silences") or []

    # Jump cuts : silences trims (proposés, jamais appliqués sans validation)
    jumpcuts = [
        {"cut_at_sec": s["end"], "removes_sec": s["duration_sec"], "kind": "jump_cut"}
        for s in silences
    ]

    # Smash audio : candidats climax du Directeur (ducking -12 dB / 0.8 s par défaut)
    smash = [
        {"at_sec": c, "duck_db": -12, "duration_sec": 0.8, "kind": "smash_cut"}
        for c in (analysis.get("climax_proposals") or [])
    ]

    out = {
        "jump_cut_proposals": jumpcuts,
        "smash_audio_proposals": smash,
        "broll_proposals": [],   # rempli par l'opérateur (numéros) — jamais auto
        "flash_proposals": [],
    }

    # Flash blanc : seulement si un B-roll futur sera placé — la doctrine dit
    # ENTRÉE de B-roll uniquement ; sans B-roll demandé, zéro flash proposé.
    # (anti-saturation : flash sans changement d'état = stroboscope interdit)

    if with_whisper and (analysis.get("whisper") or {}).get("available"):
        pl = analysis["whisper"].get("punchline_proposal_sec")
        if pl is not None and 0 < pl < duration:
            out["punchline"] = {
                "at_sec": pl,
                "silence_before_punchline": True,
                "note": "0,3-0,5 s de silence total avant la chute (spec §5)",
            }
    return out


def build_caviar_manifest(video: Path, source_meta: dict | None = None,
                          with_whisper: bool = True) -> dict:
    """Analyse une vidéo FINIE → caviar_manifest complet (verdict + propositions)."""
    caviar = _director()
    meta = probe(video)
    duration = meta["duration_sec"] or float(source_meta or {}).get("duration_sec", 0) or 30.0

    # Verdict d'entrée — la vidéo doit être saine avant toute analyse
    entry_ok, entry_errors = [], []
    if meta["codec"] not in ("h264", "vp9", "hevc", "av1"):
        entry_errors.append(f"codec {meta['codec']} non lisible")
    if not meta["has_audio"]:
        entry_errors.append("pas de piste audio (porte P-AUD du bras armé)")
    if meta["width"] <= 0:
        entry_errors.append("dimensions illisibles")
    entry_ok = not entry_errors

    analysis = caviar.analyze_clip(video, duration, with_whisper=with_whisper) if entry_ok else {}
    silences_count = analysis.get("silence_count", 0)
    max_silences = load_budget()["silences"]["max_before_refusal"]

    # Refus documenté : trop de silences → « segment mauvais, prends un autre »
    if silences_count > max_silences:
        refused = (f"segment mauvais : {silences_count} silences > {max_silences} — "
                   f"{load_budget()['silences']['refusal_message']}")
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now(),
            "source_file": video.name,
            "probe": meta,
            "verdict": "REFUSED",
            "refusal_reason": refused,
            "budget": compute_budget({}, silences_count, duration),
            "proposals": {},
            "note": "Aucun manifeste toxique n'est émis — diagnostic renvoyé à l'opérateur.",
        }

    narrative_hint = (source_meta or {}).get("narrative") or {}
    budget = compute_budget(narrative_hint, silences_count, duration)
    proposals = _proposals_from_analysis(analysis, duration, with_whisper) if entry_ok else {}

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now(),
        "generator": "HEISENBERG (sous-frégate Caviar — F03_PICTOR)",
        "source_file": video.name,
        "probe": meta,
        "verdict": "OK" if entry_ok else "BLOCKED",
        "entry_gate": {"ok": entry_ok, "errors": entry_errors},
        "analysis": {
            "silence_count": silences_count,
            "speech_ratio": analysis.get("speech_ratio"),
            "climax_candidates": analysis.get("climax_proposals") or [],
            "whisper": analysis.get("whisper"),
        },
        "budget": budget,
        "proposals": proposals,
        "doctrine": {
            "perturabo": "le OÙ/QUOI — il tranche les propositions, écrit l'accroche, choisit les numéros B-roll",
            "lacrimae": "le COMMENT — courbes, synchro, flashs, budgets, portes",
            "warsmith": "valide au gate ; toute décision créative finale lui revient",
        },
        "notes": [
            "PROPOSITIONS uniquement — rien n'est appliqué sans validation pack/manifeste + opérateur",
            "flash blanc à l'ENTRÉE de chaque B-roll, jamais à la sortie (spec §1)",
            "SFX uniquement à l'entrée des B-rolls (règle Warsmith anti-saturation)",
            "pas de vidéo = pas de B-roll (si pas de candidat, rien n'est proposé)",
        ],
    }
    return manifest


# ═══════════════════════════════════════════════════════════════════
# LEDGER — la mémoire de la frégate (confinée, ARCHIVUM-friendly)
# ═══════════════════════════════════════════════════════════════════

def ledger_write(entry: dict, kind: str = "manifest") -> None:
    """Écrit dans LEDGER/ — la frégate ne mélange jamais ses journaux."""
    ledger = HEISENBERG_ROOT / "LEDGER"
    ledger.mkdir(parents=True, exist_ok=True)
    file = ledger / ("manifest_ledger.json" if kind == "manifest" else "gate_history.json")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {"schema_version": "dev10.heisenberg-ledger.v1", "entries": []}
    data["entries"] = (data.get("entries") or [])[-499:] + [entry]
    data["updated_at"] = now()
    file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def emit(video: Path, out_dir: Path | None = None, with_whisper: bool = True,
         source_meta: dict | None = None) -> dict:
    """Reçoit une vidéo finie → écrit OUT/caviar_manifest_<stem>.json + ledger."""
    out_dir = out_dir or (HEISENBERG_ROOT / "OUT")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_caviar_manifest(video, source_meta=source_meta, with_whisper=with_whisper)
    out_path = out_dir / f"caviar_manifest_{video.stem}.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    _log(f"  [✓] HEISENBERG : manifeste émis → {out_path}")
    ledger_write({
        "at": now(),
        "kind": "emit",
        "video": video.name,
        "verdict": manifest.get("verdict"),
        "spend_units": (manifest.get("budget") or {}).get("spend_units"),
        "out_file": out_path.name,
    }, kind="manifest")
    if manifest.get("verdict") == "REFUSED":
        _log(f"  [✗] REFUS : {manifest.get('refusal_reason')}")
    return manifest


# ═══════════════════════════════════════════════════════════════════
# CHUNK PACK — la part de PERTURABO (montage_instructions additionnelles)
# ═══════════════════════════════════════════════════════════════════

def emit_pack_chunk(manifest_path: Path) -> dict:
    """Extrait la portion à embarquer dans le pack PUR (champs v2 OPTIONNELS).

    Rétrocompatibilité garantie : champs absents = comportement pack v1.
    PERTURABO relit, tranche (garde/modifie/rejette), et stampé son pack.
    """
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    proposals = m.get("proposals") or {}
    chunk = {
        "schema_version": SCHEMA_VERSION,
        "origin": "HEISENBERG",
        "note": "à intégrer dans montage_instructions du pack par PERTURABO — optionnel, v1-compatible",
        "narrative": {
            "energy_curve_hint": m.get("analysis", {}).get("climax_candidates"),
            "is_climax_proposals": m.get("analysis", {}).get("climax_candidates"),
        },
        "jump_cut_proposals": proposals.get("jump_cut_proposals") or [],
        "smash_audio_proposals": proposals.get("smash_audio_proposals") or [],
        "punchline": proposals.get("punchline"),
        "broll_available_numbers": sorted(
            int(n) for n in (load_registry().get("clips") or {}).keys()),
    }
    return chunk


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main() -> int:
    p = argparse.ArgumentParser(description="HEISENBERG — sous-frégate Caviar (F03_PICTOR)")
    p.add_argument("--manifest", type=Path, default=None,
                   help="vidéo FINIE (MP4) à analyser — OUT de F03_PICTOR")
    p.add_argument("--batch", type=Path, default=None,
                   help="dossier IN/ : analyse toutes les vidéos finies")
    p.add_argument("--out", type=Path, default=None, help="dossier OUT (défaut HEISENBERG/OUT)")
    p.add_argument("--no-whisper", action="store_true", help="désactive l'analyse CPU optionnelle")
    p.add_argument("--emit-pack-chunk", type=Path, default=None, metavar="MANIFEST_JSON",
                   help="extrait le chunk à embarquer dans le pack PERTURABO")
    p.add_argument("--broll", type=str, default=None, metavar="'met le numéro 1'",
                   help="résout un ordre B-roll numéroté (démo du contrat bras armé)")
    p.add_argument("--broll-emotion", type=str, default=None, metavar="moqueur",
                   help="propose des numéros B-roll par émotion (PERTURABO tranche)")
    args = p.parse_args()

    _log(f"\n═══ HEISENBERG — sous-frégate Caviar — {now()} ═══")
    _log("  'I am the one who knocks.' — analyse, budgets, propositions ; jamais de décision créative.")

    if args.broll:
        nums = parse_broll_order(args.broll)
        for n in nums:
            _log(f"  B-roll {n} → {json.dumps(resolve_broll_number(n), ensure_ascii=False)}")
        return 0
    if args.broll_emotion:
        _log(f"  Émotion « {args.broll_emotion} » → numéros candidats : {suggest_broll_by_emotion(args.broll_emotion)}")
        return 0
    if args.emit_pack_chunk:
        chunk = emit_pack_chunk(args.emit_pack_chunk)
        out = args.emit_pack_chunk.with_name(args.emit_pack_chunk.stem + "_pack_chunk.json")
        out.write_text(json.dumps(chunk, indent=2, ensure_ascii=False), encoding="utf-8")
        _log(f"  [✓] chunk PERTURABO émis → {out}")
        return 0

    videos: list[Path] = []
    if args.manifest:
        videos = [args.manifest]
    elif args.batch:
        videos = sorted(p for p in args.batch.iterdir()
                        if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"))
    else:
        p.print_help()
        return 1

    ok = True
    for v in videos:
        _log(f"\n── {v.name}")
        try:
            m = emit(v, out_dir=args.out, with_whisper=not args.no_whisper)
            ok = ok and m.get("verdict") in ("OK", "REFUSED")
        except Exception as exc:
            _log(f"  [✗] échec : {exc}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
