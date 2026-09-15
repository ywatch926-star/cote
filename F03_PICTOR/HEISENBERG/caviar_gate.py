#!/usr/bin/env python3
"""CAVIAR_GATE — Groupe 3 : double barrage rendu (Budget d'Attention).

Doctrine (spec CAVIAR §4) : la frégate refuse à l'ÉMISSION (heisenberg.py) et
LACRIMAE vérifie au RENDU. Deux barrages, mêmes chiffres, même source de
vérité : caviar_budget.json (miroir dans F03_PICTOR/CODEBASE/src/data/).

Ce gate lit le bloc `caviar` du pur_manifest du pack et échoue DUR si :
  - la dépense du pack > max_spend_units (55 u) ou un cap est dépassé ;
  - un flash est placé hors entrée de B-roll ;
  - un SFX existe hors entrée de B-roll ;
  - un B-roll est demandé sans fichier résolu (« pas de vidéo = pas de B-roll ») ;
  - deux événements visuels forts se chevauchent (règle élément unique).

Usage :  python3 caviar_gate.py --manifest <pur_manifest.json> [--budget <caviar_budget.json>]
Exit 0 = conforme · Exit 1 = rouge dure (le rendu CI échoue).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

COST_OF = {"brolls": "broll", "smash_audio": "smash", "punchins": "punchin", "jump_cuts": "jumpcut"}


def event_time(key: str, e: dict) -> float:
    return float(e.get("cut_at_sec") or 0.0) if key == "jump_cuts" else float(e.get("at_sec") or 0.0)


def check_caviar_block(caviar: dict, budget: dict, fps: float, label: str) -> list[str]:
    """Vérifie UN bloc caviar → liste d'erreurs (vide = conforme)."""
    events = {
        k: (caviar.get(k) if isinstance(caviar.get(k), list) else [])
        for k in ("jump_cuts", "punchins", "brolls", "smash_audio")
    }
    errors: list[str] = []

    # 1) Caps + dépense (PAR entrée — chaque vidéo a son propre Budget d'Attention)
    counts = {k: len(v) for k, v in events.items()}
    ev = budget["events"]
    spend = (counts["brolls"] * ev["broll"]["cost_units"]
             + counts["smash_audio"] * ev["smash"]["cost_units"]
             + counts["punchins"] * ev["punchin"]["cost_units"]
             + counts["jump_cuts"] * ev["jumpcut"]["cost_units"])
    if spend > budget["max_spend_units"]:
        errors.append(f"{label} : dépense {spend}u > {budget['max_spend_units']}u (Budget d'Attention)")
    for key, cfg_key in COST_OF.items():
        if counts[key] > ev[cfg_key]["max_per_clip"]:
            errors.append(f"{label} : cap {cfg_key} dépassé : {counts[key]} > {ev[cfg_key]['max_per_clip']}")

    # 2) Pas de vidéo = pas de B-roll
    for b in events["brolls"]:
        if not str(b.get("file") or "").strip():
            errors.append(f"{label} : B-roll numéro {b.get('numero')} sans fichier résolu — pas de vidéo, pas de B-roll")

    # 3) Flash UNIQUEMENT à l'entrée des B-rolls (frame du flash = frame du B-roll)
    broll_frames = {round(float(b.get("at_sec") or 0.0) * fps) for b in events["brolls"]}
    for fl in caviar.get("flashes", []):
        raw = float(fl.get("frame", fl.get("at_sec") or 0.0))
        fr = round(raw * (fps if raw < 100000 else 1))
        if fr not in broll_frames:
            errors.append(f"{label} : flash hors entrée de B-roll à la frame {fr} (spec CAVIAR §1)")

    # 4) SFX UNIQUEMENT à l'entrée des B-rolls
    for s in caviar.get("sfx", []):
        raw = float(s.get("frame", s.get("at_sec") or 0.0))
        fr = round(raw * (fps if raw < 100000 else 1))
        if fr not in broll_frames:
            errors.append(f"{label} : SFX hors entrée de B-roll à la frame {fr} (règle Warsmith anti-saturation)")

    # 5) Élément unique — pas de chevauchement d'événements visuels forts
    window = float(budget.get("unique_element_rule", {}).get("window_sec", 0.05))
    strong = ([(event_time("brolls", b), "broll") for b in events["brolls"]]
              + [(event_time("punchins", p), "punchin") for p in events["punchins"]])
    for i in range(len(strong)):
        for j in range(i + 1, len(strong)):
            if abs(strong[i][0] - strong[j][0]) < max(window, 1e-6):
                errors.append(f"{label} : deux événements forts à moins de {window}s : {strong[i]} vs {strong[j]}")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate Budget d'Attention côté rendu (rouge dure)")
    ap.add_argument("--manifest", type=Path, required=True, help="pur_manifest.json du pack (bloc caviar)")
    ap.add_argument("--budget", type=Path, default=None, help="caviar_budget.json (défaut : miroir F03)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent  # HEISENBERG/
    budget_path = args.budget or (root / "caviar_budget.json")
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fps = float(manifest.get("fps") or 30)

    # Manifeste MULTI-ENTRÉES (agrégat) : le budget est vérifié PAR entrée.
    # Manifeste simple (1 runner) : le bloc caviar racine est vérifié seul.
    entries = manifest.get("entries")
    if isinstance(entries, list) and entries:
        blocks = [((e.get("caviar") or {}), f"entrée {e.get('angle_id') or e.get('source_id') or i}")
                  for i, e in enumerate(entries)]
    else:
        blocks = [(manifest.get("caviar") or {}, "pack")]

    errors: list[str] = []
    active = 0
    for caviar, label in blocks:
        if not caviar.get("enabled"):
            continue
        active += 1
        errors.extend(check_caviar_block(caviar, budget, fps, label))

    # Bloc caviar absent partout : rien à vérifier, pack v1-compatible.
    if active == 0:
        print("[caviar_gate] bloc caviar absent/désactivé — pack v1-compatible, gate neutre.")
        return 0

    spend = sum(
        len(c.get("brolls") or []) * budget["events"]["broll"]["cost_units"]
        + len(c.get("smash_audio") or []) * budget["events"]["smash"]["cost_units"]
        + len(c.get("punchins") or []) * budget["events"]["punchin"]["cost_units"]
        + len(c.get("jump_cuts") or []) * budget["events"]["jumpcut"]["cost_units"]
        for c, _ in blocks if c.get("enabled")
    )

    if errors:
        print("[caviar_gate] ✗ ROUGE — divergences Budget d'Attention :")
        for e in errors:
            print(f"   - {e}")
        return 1

    print(f"[caviar_gate] ✓ VERT — dépense {spend}u/{budget['total_budget_units']}u, "
          f"respiration {budget['total_budget_units'] - spend}u, caps respectés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
