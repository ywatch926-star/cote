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
import re
import sys
from pathlib import Path

COST_OF = {"brolls": "broll", "smash_audio": "smash", "punchins": "punchin", "jump_cuts": "jumpcut"}


def event_time(key: str, e: dict) -> float:
    return float(e.get("cut_at_sec") or 0.0) if key == "jump_cuts" else float(e.get("at_sec") or 0.0)


def load_registry() -> dict:
    """Registre B-roll (miroir rendu si présent, sinon source HEISENBERG)."""
    for p in (Path(__file__).resolve().parents[2] / "F03_PICTOR" / "CODEBASE" / "src" / "data" / "caviar_registry.json",
              Path(__file__).resolve().parent / "BROLL" / "registry.json"):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def to_v1_block(caviar: dict, registry: dict, label: str, warnings: list[str]) -> dict:
    """Normalise un bloc v2 (partition F00D brute) en forme v1 du moteur.

    La note décrivait le manifeste (events.broll/events.punch_ins) ; le pack
    réel porte panels[] et smash_audio[] au TOP (vérifié sur voxc-2) — les
    deux formes sont acceptées. Les broll_id sont résolus via le registre
    (sémantique puis numéroté) ; un id non résolu = AVERTISSEMENT (l'événement
    sera déposé au rendu — « pas de vidéo = pas de B-roll »).
    """
    events = caviar.get("events") if isinstance(caviar.get("events"), dict) else {}
    looks_v2 = (isinstance(caviar.get("panels"), list) or bool(events)
                or "silence_trims" in caviar or caviar.get("bound") is True)
    if not looks_v2:
        return caviar  # déjà en forme v1

    semantic = registry.get("semantic") or {}
    clips = registry.get("clips") or {}
    brolls = []
    for b in (caviar.get("panels") or []) + (events.get("broll") or []):
        if not isinstance(b, dict):
            continue
        bid = str(b.get("broll_id") or "")
        sfx = str(b.get("sfx") or "impact")
        file = ""
        reg = semantic.get(bid) or semantic.get(bid.upper()) or {}
        if reg.get("file"):
            file, sfx = str(reg["file"]), str(reg.get("sfx") or sfx)
        elif bid.isdigit() and (clips.get(bid) or {}).get("file"):
            file = str(clips[bid]["file"])
        if not file:
            warnings.append(f"{label} : broll_id {bid!r} non résolu dans le registre — déposé au rendu (pas de vidéo = pas de B-roll)")
        brolls.append({"at_sec": float(b.get("start_sec") or b.get("at_sec") or 0),
                       "numero": bid, "file": file, "sfx": sfx})
    jump = [{"cut_at_sec": float(t.get("cut_at_sec", t.get("start_sec", 0))),
             "removes_sec": float(t.get("removes_sec", t.get("duration_sec", 0)))}
            for t in (caviar.get("silence_trims") or []) if isinstance(t, dict)]
    punch = [{"at_sec": float(z.get("at_sec", z.get("start_sec", 0))),
              "scale_to": float(z.get("scale_to", z.get("crop_zoom", 1.08)))}
             for z in (events.get("punch_ins") or []) + (caviar.get("punch_ins") or []) if isinstance(z, dict)]
    smash = [{"at_sec": float(s.get("at_sec", s.get("start_sec", 0))),
              "duck_db": float(s.get("duck_db", -12)),
              "duration_sec": float(s.get("duration_sec", 0.8))}
             for s in (events.get("smash_audio") or []) + (caviar.get("smash_audio") or []) if isinstance(s, dict)]
    return {"enabled": True, "jump_cuts": jump, "punchins": punch,
            "brolls": brolls, "smash_audio": smash}


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


def check_pack_v2(pack: dict, budget: dict) -> list[str]:
    """Portes v2 (note technique PERTURABO 2026-09-15) sur le pack BRUT.

    Vérifie ce que le moteur ne peut pas vérifier : la LÉGALITÉ du pack
    (gates opérateur, checksum, hiérarchie, horodatage, resolution_at).
    Le budget lui-même est revérifié par check_caviar_block (notre recalcul
    indépendant) — le pack ment → rouge.
    """
    errors: list[str] = []
    partition = pack.get("caviar_partition") if isinstance(pack.get("caviar_partition"), dict) else None
    if partition is None:
        return errors  # pas une partition v2 → portes v2 non applicables

    # 1) Porte d'entrée : review — seuls les packs ALL_GATES_GO sont exécutables
    review = pack.get("review") or {}
    if review.get("gate_state") != "ALL_GATES_GO" or review.get("status") != "VALIDATED":
        errors.append(
            f"review non exécutable : gate_state={review.get('gate_state')!r} "
            f"status={review.get('status')!r} (attendu : ALL_GATES_GO / VALIDATED — DRAFT ≠ exécutable)"
        )

    # 2) f06_gate.mode == caviar_bound v3.0.0
    f06 = (pack.get("chain_of_custody") or {}).get("f06_gate") or {}
    mode = str(f06.get("mode") or "")
    if mode and not mode.startswith("caviar_bound"):
        errors.append(f"f06_gate.mode={mode!r} ≠ caviar_bound — pack v2 incohérent")

    # 3) Hiérarchie : si partition présente, F06 ne produit AUCUN cut/zoom propre
    mi = pack.get("montage_instructions") or {}
    body = mi.get("body") or {}
    own_cuts = [c for c in (body.get("cuts") or []) if c]
    own_zooms = [z for z in (body.get("zooms") or []) if z]
    if own_cuts or own_zooms:
        errors.append(
            f"hiérarchie violée : partition caviar présente ET body.cuts={len(own_cuts)} "
            f"body.zooms={len(own_zooms)} non vides — régression F06 à signaler"
        )

    # 4) checksum16 : cohérence interne binding ↔ chain_of_custody (le pack est
    #    immuable : les deux DOIVENT être identiques). La vérif contre le
    #    manifeste livré se fait via --manifest-caviar.
    binding = mi.get("caviar_binding") or {}
    custody = (pack.get("chain_of_custody") or {}).get("f00d_partition") or {}
    ck_binding = str(binding.get("manifest_sha256_16") or "")
    ck_custody = str(custody.get("checksum16") or "")
    if ck_binding and ck_custody and ck_binding != ck_custody:
        errors.append(f"checksum16 divergents : binding={ck_binding!r} ≠ custody={ck_custody!r} — refuse le rendu")

    # 5) Horodatage : le manifeste doit PRÉCÉDER le pack
    binding_run = str(binding.get("run_id") or partition.get("run_id") or "")
    if binding_run:
        m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", binding_run)
        pack_at = str(pack.get("generated_at") or "")
        if m and pack_at:
            manifest_t = m.group(1)
            if manifest_t[:19] > pack_at[:19]:
                errors.append(f"horodatage impossible : manifeste ({manifest_t}) APRÈS le pack ({pack_at[:19]})")

    # 6) resolution_at : aucun événement après la résolution narrative
    res_at = partition.get("resolution_at")
    if isinstance(res_at, (int, float)) and res_at > 0:
        late = []
        for b in partition.get("panels") or []:
            if float(b.get("start_sec") or 0) >= float(res_at):
                late.append(f"broll {b.get('broll_id')} @ {b.get('start_sec')}s")
        ev = partition.get("events") or {}
        for z in (ev.get("punch_ins") or []) + (partition.get("punch_ins") or []):
            if float(z.get("at_sec") or z.get("start_sec") or 0) >= float(res_at):
                late.append(f"punch_in @ {z.get('at_sec', z.get('start_sec'))}s")
        for s in (ev.get("smash_audio") or []) + (partition.get("smash_audio") or []):
            if float(s.get("at_sec") or 0) >= float(res_at):
                late.append(f"smash @ {s.get('at_sec')}s")
        if late:
            errors.append(f"événements après resolution_at ({res_at}s) : {', '.join(late)} — interdit par la note §3.5")

    # 7) budget_state.caps_respected croisé avec NOTRE recalcul indépendant
    bstate = partition.get("budget_state") or {}
    counts = bstate.get("counts") or {}
    ev_cfg = budget["events"]
    n_panels = len(partition.get("panels") or []) + len((partition.get("events") or {}).get("broll") or [])
    n_smash = counts.get("smash_audio", 0) or len((partition.get("events") or {}).get("smash_audio") or [])
    n_punch = counts.get("punch_ins", 0) or len((partition.get("events") or {}).get("punch_ins") or [])
    n_cuts = counts.get("jump_cuts", 0) or len(partition.get("silence_trims") or [])
    spend = (n_panels * ev_cfg["broll"]["cost_units"] + n_smash * ev_cfg["smash"]["cost_units"]
             + n_punch * ev_cfg["punchin"]["cost_units"] + n_cuts * ev_cfg["jumpcut"]["cost_units"])
    if spend > budget["max_spend_units"]:
        errors.append(f"budget partition : dépense recalculée {spend}u > {budget['max_spend_units']}u — refuse le rendu")
    if bstate.get("caps_respected") is False:
        errors.append("budget_state.caps_respected=false — la partition se déclare hors caps")
    declared = bstate.get("spent_units")
    if isinstance(declared, int) and declared != spend:
        errors.append(f"budget_state.spent_units={declared} ≠ recalcul {spend}u — partition incohérente")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate Budget d'Attention côté rendu (rouge dure)")
    ap.add_argument("--manifest", type=Path, required=True, help="pur_manifest.json du pack (bloc caviar)")
    ap.add_argument("--budget", type=Path, default=None, help="caviar_budget.json (défaut : miroir F03)")
    ap.add_argument("--pack-v2", type=Path, default=None,
                    help="pack v2 BRUT (production_pack_*.json) — portes v2 : review/checksum/hiérarchie/resolution_at/budget")
    ap.add_argument("--manifest-caviar", type=Path, default=None,
                    help="caviar_manifest.json (F00D) — vérifie checksum16 contre le binding du pack")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent  # HEISENBERG/
    budget_path = args.budget or (root / "caviar_budget.json")
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fps = float(manifest.get("fps") or 30)

    # Portes v2 sur le pack BRUT (avant conversion) : review, checksum,
    # hiérarchie, horodatage, resolution_at, budget_state croisé.
    pack_errors: list[str] = []
    if args.pack_v2:
        pack_raw = json.loads(args.pack_v2.read_text(encoding="utf-8"))
        pack_errors = check_pack_v2(pack_raw, budget)
        # checksum16 contre le manifeste F00D livré (si fourni)
        if args.manifest_caviar:
            import hashlib
            manifest_cav = args.manifest_caviar.read_bytes()
            ck = hashlib.sha256(manifest_cav).hexdigest()[:16]
            binding = ((pack_raw.get("montage_instructions") or {}).get("caviar_binding") or {})
            custody = ((pack_raw.get("chain_of_custody") or {}).get("f00d_partition") or {})
            expected = str(binding.get("manifest_sha256_16") or custody.get("checksum16") or "")
            if expected and ck != expected:
                pack_errors.append(f"checksum16 du manifeste livré ({ck}) ≠ attendu ({expected}) — refuse le rendu")
    if pack_errors:
        print("[caviar_gate] ✗ ROUGE — pack v2 non conforme :")
        for e in pack_errors:
            print(f"   - {e}")
        return 1
    if args.pack_v2:
        print("[caviar_gate] ✓ pack v2 — portes review/checksum/hiérarchie/horodatage/resolution_at/budget : OK")

    # Manifeste MULTI-ENTRÉES (agrégat) : le budget est vérifié PAR entrée.
    # Manifeste simple (1 runner) : le bloc caviar racine est vérifié seul.
    # Chaque bloc est normalisé v2→v1 avant vérification (partition F00D).
    registry = load_registry()
    entries = manifest.get("entries")
    if isinstance(entries, list) and entries:
        raw_blocks = [((e.get("caviar") or e.get("caviar_partition") or {}),
                       f"entrée {e.get('angle_id') or e.get('source_id') or i}")
                      for i, e in enumerate(entries)]
    else:
        raw_blocks = [(manifest.get("caviar") or manifest.get("caviar_partition") or {}, "pack")]

    warnings: list[str] = []
    blocks = [(to_v1_block(raw, registry, label, warnings), label) for raw, label in raw_blocks]
    for w in warnings:
        print(f"[caviar_gate] ⚠ {w}")

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
