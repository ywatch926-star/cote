# HEISENBERG — sous-frégate Caviar du bras armé (embarquée dans F03_PICTOR)

> Honneur à Walter White : la pureté, c'est tout. Nous visons le 99 % —
> pas plus d'effets, une précision diabolique du dosage.

**Date** : 2026-09-14 · **Statut** : implémentée (Groupe 2 du plan d'implémentation) ·
**Moteur d'analyse** : Directeur Caviar Groupe 1 (`F00_INGEST/CODEBASE/caviar.py`) — zéro doublon.

---

## 1. Mission unique

Recevoir les **vidéos FINIES** produites par F03_PICTOR (validées par le gate
qui suit F03), les **analyser**, et émettre un **`caviar_manifest_<stem>.json`
par vidéo finale** — le JSON que PERTURABO embarque dans son pack et que le
bras armé transforme en clip caviar au rendu.

```
F03_PICTOR rend pur_<angle>_finale.mp4
        │  (gate suite F03 : bundle complet, P-AUD audio présent)
        ▼
HEISENBERG/IN/  ← la vidéo finie entre ici
        │
        ▼
[heisenberg.py]  analyse (Directeur) + Budget d'Attention + verdict
        │
        ▼
HEISENBERG/OUT/caviar_manifest_<stem>.json   (+ LEDGER/)
        │
        ▼
PERTURABO relit le manifeste (+ chunk optionnel), tranche, stampe le pack
        │
        ▼
Le bras armé exécute le pack : B-roll numéroté → flash entrée + SFX couplé
```

## 2. Architecture (tout vit dans `F03_PICTOR/HEISENBERG/`)

| Élément | Rôle |
|---|---|
| `heisenberg.py` | le moteur — analyse, budget, émission, CLI |
| `caviar_budget.json` | **Budget d'Attention — source de vérité UNIQUE** (ingéré aussi par les gates P-CAV) |
| `IN/` | vidéos finies reçues de F03_PICTOR |
| `OUT/` | manifestes caviar émis · `OUT/hold/` = diagnostics des REFUSED |
| `LEDGER/` | `manifest_ledger.json` + `gate_history.json` — mémoire confinée de la frégate |
| `BROLL/registry.json` | registre **numéroté** — le bras armé seul connaît les fichiers |
| `BROLL/FILES/` | les .mp4 réels (opérateur, jamais commités) |
| `BROLL/candidates/` | fiches d'ajout (numéro candidat → décision opérateur) |

Mémoire globale : lecture de l'ARCHIVUM (patterns, pieges) ; écriture confinée
au LEDGER de la frégate aujourd'hui, vers `ARCHIVUM/narrativum/` demain
(Groupe 4 — après validation de la doctrine de conservation).

## 3. Le Budget d'Attention (100 unités / clip de 30 s)

La frégate **dépense avant d'écrire** :

| Événement | Coût | Cap indépendant |
|---|---|---|
| B-roll + flash + SFX (le trio inséparable) | 12 u | ≤ 3 par clip |
| Smash audio (ducking au climax) | 8 u | ≤ 2 |
| Punch-in (zoom) | 6 u | ≤ 4, espacés ≥ 2 s |
| Jump cut (trim silence) | 1 u | ≤ 8 |

**Règles de survie** :
- dépense totale **≤ 55 u** → les 45 u restantes = respiration (source seule ≥ 60-70 % de la timeline) ;
- **plus de 8 silences à trimmer → REFUS d'émettre** (« segment mauvais, prends un autre ») ;
- dépassement → **pas de manifeste toxique** : diagnostic renvoyé à l'opérateur.

## 4. Le contrat B-roll numéroté

1. PERTURABO écrit l'**émotion** à illustrer (`moqueur`, `chute`, `climax`…).
2. Il dit : **« met le numéro 1 »**.
3. Heisenberg fait le lien numéro → fichier (référence neutre `broll#1` —
   jamais de chemin exposé), pose le **flash blanc à l'ENTRÉE** du B-roll
   (jamais à la sortie) et le **SFX couplé sur la même frame**.
4. **Pas de vidéo = pas de B-roll** : sans fichier réel dans `BROLL/FILES/`,
   le numéro est indisponible et rien n'est proposé.
5. Le SFX vit **uniquement à l'entrée des B-rolls** — seul endroit autorisé
   (règle anti-saturation du Warsmith).

## 5. Verdicts d'émission

| Verdict | Signification | Conséquence |
|---|---|---|
| `OK` | vidéo saine, propositions émises | manifeste écrit dans OUT/ + ledger |
| `BLOCKED` | vidéo illisible (codec, audio absent) | manifeste BLOCKED, rien de rendu |
| `REFUSED` | segment mauvais (> 8 silences) | **aucun manifeste toxique** — diagnostic dans OUT/hold/ |

## 6. Usage

```bash
python3 F03_PICTOR/HEISENBERG/heisenberg.py --manifest <video_finie.mp4>
python3 F03_PICTOR/HEISENBERG/heisenberg.py --batch F03_PICTOR/HEISENBERG/IN/
python3 F03_PICTOR/HEISENBERG/heisenberg.py --emit-pack-chunk OUT/caviar_manifest_X.json
python3 F03_PICTOR/HEISENBERG/heisenberg.py --broll "met le numéro 1"
python3 F03_PICTOR/HEISENBERG/heisenberg.py --broll-emotion moqueur
python3 F03_PICTOR/HEISENBERG/tests/test_heisenberg.py     # 20 tests
```

## 7. Frontières (non négociables)

- Heisenberg **propose**, ne décide jamais (PERTURABO = OÙ/QUOI, Warsmith tranche).
- Pas d'accroche, pas de choix de segment, pas de style.
- `speed` 1.05 intouchable (décision opérateur verrouillée).
- Champs du chunk **optionnels et rétrocompatibles v1** (absents = comportement inchangé).
