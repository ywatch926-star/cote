# LACRIMAE dev10 — GATES CAVIAR (P-CAV) — Montage narratif

**Spec mère** : `TRACKING/CAVIAR_SPEC_PERTURABO.md` · **Code** : `F00_INGEST/CODEBASE/caviar.py`
**Statut (2026-09-14)** : Groupe 1 implémenté (Directeur + Porte P-CAV) + **Groupe 2 : HEISENBERG** —
sous-frégate d'émission opérationnelle (`F03_PICTOR/HEISENBERG/`, voir `TRACKING/HEISENBERG_GATES.md`)
qui consomme le Directeur et émet un caviar_manifest par vidéo finale. Phase 3 (rendu B-roll/narratif) non démarrée.
**Doctrine** : PERTURABO = le OÙ/QUOI · LACRIMAE = le COMMENT · Warsmith tranche.
**Champs narratifs absents du pack = bypass intégral** (packs v1 inchangés).

## Porte P-CAV (bloquante, dans f00_pur.py après G0)

| Règle | Budget / limite | Référence spec |
|---|---|---|
| `narrative.hook_type` | ∈ {climax_first, reframe, question} | §5 |
| `narrative.is_climax` | liste de secondes ≥ 0, dans le segment | §5 |
| `narrative.energy_curve` | ∈ {rise, peak, fall} | §5 |
| `broll[]` | ≤ 3 par clip | §5 |
| `broll[].duration_frames` | ≤ 45 (1,5 s à 30 fps) | §5 |
| `broll[].sfx` | OBLIGATOIRE (visuel sans son = impression de bug) | §5 |
| `broll[]` vs `resolution_at` | aucun B-roll démarre pendant la résolution | §5 |
| Flashs blancs | ≤ 3, espacés ≥ 1,5 s, ENTRÉE de B-roll uniquement | §1+§5 |
| Zooms (punch-ins) | ≤ 4, espacés ≥ 2 s | §5 |
| Règle de l'élément unique | 2 événements visuels forts à < 50 ms d'écart = rouge | §5 |
| Flash de zoom ↔ SFX | SFX requis sur la même frame (tolérance 50 ms) | §1 |
| `audio_design.duck_at_climax.db` | ≤ 0 | §5 |

Échec P-CAV → **job rouge** (le pack retourne à PERTURABO, comme G0).
Champ présent mais invalide = rouge ; champ absent = bypass.

## Le Directeur (advisory — ne bloque JAMAIS)

Après G3, `f00_pur.py` lance `caviar.analyze_clip()` et écrit
`OUT/pur/pur_caviar_<angle_id>.json` + résumé dans `pur_sources.json` (clé `caviar`) :

- **Carte des silences** (ffmpeg silencedetect, > 250 ms, seuil -35 dB) → `trim_proposals[]` (futurs Jump Cuts — appliqués seulement sur validation manifeste/opérateur, Phase 3+).
- **Carte des amplitudes** (RMS 50 ms, clusters mean+2σ) → `climax_proposals[]` (candidats `is_climax` à soumettre à PERTURABO).
- **Whisper CPU optionnel** (faster-whisper base/int8) → timestamps de mots, `punchline_proposal_sec` (dernier mot avant la plus longue pause), fins de phrases fortes. Indisponible = non-bloquant.

Un échec d'analyse est **toléré et journalisé** (advisory) : le job continue.

## Tests

`python3 F00_INGEST/tests/test_caviar.py` — 20 vérifications (bypass v1, pack valide,
chaque budget bloquant, schéma, clusters RMS synthétiques, détection de silence ffmpeg).

## Phases restantes (GO opérateur requis, une par une)

- **Groupe 3 — Rendu narratif** : Jump Cuts (table source↔timeline + recalcul G2/agrégation), ducking audio, rupture d'overlay au climax, rendu B-roll NUMÉROTÉ (registre Heisenberg : « met le numéro 1 » → flash entrée + SFX couplé, ≤45 frames).
- **Groupe 4 — Conservation** : ARCHIVUM/narrativum (gate_history, retention_log A/B caviar vs basique, lessons) + Pacing intelligent (densité des trims pilotée par `energy_curve`).
- **Flow/Match cut** : reporté jusqu'à preuve de rétention des groupes précédents.

> Mise à jour 2026-09-14 : les constantes de budget sont désormais partagées via
> `F03_PICTOR/HEISENBERG/caviar_budget.json` (source de vérité unique — double
> barrage frégate/gates). Les constantes de `caviar.py` restent alignées.
