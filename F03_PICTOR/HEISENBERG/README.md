# HEISENBERG — sous-frégate Caviar du bras armé (F03_PICTOR)

> *« I am the one who knocks. »* — la pureté, c'est tout. 99 %, jamais 60 %.

## Mission unique

Heisenberg reçoit les **vidéos FINIES** produites par F03_PICTOR (validées par
le gate qui suit F03), les **analyse**, et émet un **`caviar_manifest_<stem>.json`
par vidéo finale** — le JSON que PERTURABO embarque dans son pack et que le
bras armé transforme en clip caviar au rendu.

Elle ne remplace RIEN : le Directeur Caviar (Groupe 1, `F00_INGEST/caviar.py`)
reste le moteur d'analyse ; Heisenberg en est le **poste d'émission** dédié,
isolé dans F03_PICTOR, avec sa mémoire, ses budgets et sa bibliothèque B-roll.

## Architecture (tout vit ici — zéro doublon ailleurs)

```
F03_PICTOR/HEISENBERG/
├── heisenberg.py          ← le moteur (analyse, budget, émission)
├── caviar_budget.json     ← Budget d'Attention — SOURCE DE VÉRITÉ UNIQUE
├── IN/                    ← vidéos finies reçues de F03_PICTOR
├── OUT/                   ← caviar_manifest_<stem>.json émis (+ hold/ pour les REFUSED)
├── LEDGER/                ← manifest_ledger.json + gate_history.json (mémoire confinée)
├── BROLL/
│   ├── registry.json      ← registre NUMÉROTÉ (PERTURABO ne voit jamais les fichiers)
│   ├── FILES/             ← les .mp4 réels (déposés par l'opérateur, jamais commités)
│   └── candidates/        ← fiches d'ajout (numéro candidat → décision opérateur)
└── tests/test_heisenberg.py
```

## Le contrat B-roll numéroté (règle du Warsmith)

1. PERTURABO écrit l'**émotion** à illustrer (`moqueur`, `chute`, `climax`…).
2. Il dit simplement : **« met le numéro 1 »**.
3. Heisenberg (bras armé) sait **seul** quel fichier se cache derrière le
   numéro, pose le **flash blanc à l'ENTRÉE** du B-roll (jamais à la sortie)
   et le **SFX couplé sur la même frame**.
4. **Pas de vidéo = pas de B-roll** : sans fichier réel dans `FILES/`, le
   numéro est réputé indisponible et rien n'est proposé.
5. Le SFX vit **uniquement** à l'entrée des B-rolls — c'est le seul endroit
   où la doctrine autorise le SFX (anti-saturation).

```bash
python3 heisenberg.py --broll "met le numéro 1"           # → fiche complète (référence neutre broll#1)
python3 heisenberg.py --broll-emotion moqueur             # → numéros candidats (PERTURABO tranche)
```

## Le Budget d'Attention (100 unités)

Source unique : `caviar_budget.json` — LACRIMAE l'ingère dans ses gates
P-CAV (double barrage : la frégate refuse à l'émission, les gates rouges au
rendu si divergence), PERTURABO lit les mêmes chiffres pour composer.

| Événement | Coût | Cap par clip |
|---|---|---|
| B-roll + flash + SFX (trio inséparable) | 12 u | ≤ 3 |
| Smash audio (ducking au climax) | 8 u | ≤ 2 |
| Punch-in (zoom) | 6 u | ≤ 4, espacés ≥ 2 s |
| Jump cut (trim silence) | 1 u | ≤ 8 |

**Règles de survie** : dépense ≤ 55 u (le reste = respiration, source seule
≥ 60-70 % de la timeline) · **> 8 silences = REFUS d'émettre** (« segment
mauvais, prends un autre ») · jamais de manifeste toxique — diagnostic renvoyé.

## Usage

```bash
# Une vidéo finie (OUT de F03_PICTOR)
python3 F03_PICTOR/HEISENBERG/heisenberg.py --manifest F03_PICTOR/OUT/A01/pur_A01_finale.mp4

# Toutes les vidéos déposées dans IN/
python3 F03_PICTOR/HEISENBERG/heisenberg.py --batch F03_PICTOR/HEISENBERG/IN/

# La part à embarquer dans le pack PERTURABO (optionnel, v1-compatible)
python3 F03_PICTOR/HEISENBERG/heisenberg.py --emit-pack-chunk OUT/caviar_manifest_pur_A01_finale.json

# Tests
python3 F03_PICTOR/HEISENBERG/tests/test_heisenberg.py
```

## Ce que Heisenberg NE fait PAS

- Écrire une accroche, choisir un segment, décider d'un style (PERTURABO/Warsmith).
- Appliquer ses propositions d'office — tout est advisory jusqu'au pack validé.
- Toucher au `speed` 1.05 (décision opérateur verrouillée).
- Doubler la porte P-CAV : elle utilise le MÊME `caviar_budget.json`.
