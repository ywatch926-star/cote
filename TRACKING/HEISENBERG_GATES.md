# LACRIMAE dev10 — GATES HEISENBERG (H-*) — sous-frégate Caviar

**Spec mère** : `TRACKING/CAVIAR_SPEC_PERTURABO.md` · **Plan** : `TRACKING/HEISENBERG_PLAN.md`
**Code** : `F03_PICTOR/HEISENBERG/heisenberg.py` · **Budget** : `F03_PICTOR/HEISENBERG/caviar_budget.json`
**Statut (2026-09-14)** : Groupe 2 implémenté — frégate opérationnelle (IN/OUT/LEDGER/BROLL + tests 20/20).

## Position dans le pipeline

```
F03_PICTOR rend → gates existantes (bundle, P-AUD) → [HEISENBERG H0-H3] → caviar_manifest_<stem>.json
```

## Gates

| Gate | Moment | Vérification | Critère de passage |
|---|---|---|---|
| **H0 INPUT** | Entrée | Vidéo finie lisible | codec ∈ {h264, vp9, hevc, av1}, dimensions > 0 — sinon verdict `BLOCKED` |
| **H1 AUDIO** | Entrée | Piste audio présente | `has_audio=true` (miroir de la porte P-AUD du bras armé) |
| **H2 BUDGET** | Analyse | Budget d'Attention | dépense ≤ 55 u ET tous les caps respectés (broll ≤ 3, smash ≤ 2, punchin ≤ 4, jumpcut ≤ 8) |
| **H3 SILENCES** | Analyse | Segment exploitable | ≤ 8 silences — sinon **REFUSED** (« segment mauvais, prends un autre »), diagnostic → `OUT/hold/` |

## Verdicts

| Verdict | Sortie |
|---|---|
| `OK` | `OUT/caviar_manifest_<stem>.json` + entrée ledger |
| `BLOCKED` | manifeste BLOCKED (aucune proposition), ledger |
| `REFUSED` | diagnostic copié dans `OUT/hold/`, **aucun manifeste toxique**, ledger |

## Ledger (mémoire confinée)

- `LEDGER/manifest_ledger.json` — chaque émission (vidéo, verdict, dépense, fichier).
- `LEDGER/gate_history.json` — verdicts GO/NO-GO + raisons.
- Format `dev10.heisenberg-ledger.v1`, ring buffer 500 entrées.
- Plus tard (Groupe 4) : conservation vers `ARCHIVUM/narrativum/` (gate_history,
  retention_log A/B caviar vs basique, lessons) — après décision doctrinale.

## Budget d'Attention — double barrage

`caviar_budget.json` est la **source unique** : la frégate refuse à l'émission
(H2/H3) ET les gates P-CAV du bras armé restent rouges au rendu si un pack
diverge des mêmes chiffres. Un seul fichier à amender (décision opérateur),
jamais de constante dupliquée dans le code.

## Gates GROUPE 3 — rendu narratif (implémentés, 2026-09-15)

| Gate | Moment | Vérification | Critère de passage |
|---|---|---|---|
| **H-MIRROR** | CI, avant rendu | miroir budget F03 == source HEISENBERG | `diff caviar_budget.json` identique — sinon rouge dure |
| **H-ENGINE** | CI, avant rendu | moteur de rendu narratif | `npm run test:caviar` 20/20 — sinon rouge dure |
| **H-PACK** | CI, avant rendu | bloc `caviar` du pack (par entrée) | `caviar_gate.py` : dépense ≤ 55 u, caps, flash ENTRÉE-seule, SFX ENTRÉE-seule, pas de B-roll sans fichier, élément unique — sinon rouge dure (rendu annulé) |
| **H-AGGREGATE** | CI, avant publication | manifeste agrégé multi-entrées | `caviar_gate.py` sur chaque entrée — sinon AUCUN bundle final publié |
| **H-RENDER (soft)** | rendu Remotion | `buildCaviarTimeline()` en rendu | dépassement en rendu → événements DÉPOSÉS (le plus cher/tardif d'abord) + gate rouge rapporté — le MP4 reste propre, jamais saturé |

Miroir budget consommé au rendu : `F03_PICTOR/CODEBASE/src/data/caviar_budget.json`
(vérifié identique à la source HEISENBERG par H-MIRROR).

## CI (branché)

Le workflow `dev10_pur_render.yml` appelle Heisenberg après l'agrégation
(`--no-whisper` sur les runners CI, rapide et sans dépendance). Un échec
Heisenberg n'empêche PAS la publication du bundle (la frégate est advisory) —
sauf verdict REFUSED journalisé, qui remonte comme avertissement opérateur.
Les gates H-MIRROR / H-ENGINE / H-PACK / H-AGGREGATE, eux, sont **bloquants**
(divergence budget = job rouge, aucun rendu, aucun bundle).

## Tests

`python3 F03_PICTOR/HEISENBERG/tests/test_heisenberg.py` — 20 tests :
budgets, caps, refus, verdicts, B-roll numéroté (jamais de chemin exposé),
chunk pack rétrocompatible, ledger, non-régression P-CAV Groupe 1.
