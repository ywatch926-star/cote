# HEISENBERG — sous-frégate Caviar du bras armé (embarquée dans F03_PICTOR)

> Honneur à Walter White : la pureté, c'est tout. Nous visons le 99 % —
> pas plus d'effets, une précision diabolique du dosage.

**Date** : 2026-09-14 (Groupe 3 : 2026-09-15) · **Statut** : Groupe 2 + **Groupe 3 (rendu narratif) implémentés** ·
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

## 8. GROUPE 3 — le rendu narratif (implémenté, 2026-09-15)

Le bras armé transforme le bloc `caviar` du pack (décisions PERTURABO prises
 depuis le manifeste de la frégate) en rendu Remotion réel :

| Élément | Implémentation |
|---|---|
| **Jump cuts** | `buildCaviarTimeline()` : table source↔timeline en tuiles contiguës (aucun trou, aucun débordement) ; chaque tuile lit `startFrom` source ; un événement tombant DANS un silence retiré est recalé au point de coupe |
| **Punch-ins** | courbe attack/hold/release (montée sèche, tenue, redescente vers 1.0), peak plafonné à 1.15 — jamais de zoom libre |
| **B-roll numéroté** | overlay plein cadre (la voix du clip CONTINUE), flash blanc à l'ENTRÉE uniquement, SFX couplé sur la même frame ; **pas de fichier résolu = pas de B-roll** |
| **Smash audio** | ducking `caviarDuckVolumeAtFrame()` (−12 dB, rampe 2 frames) — s'activera dès qu'une piste musicale PUR existera |
| **fx_mode=off** | « clip normal » : punch-ins/flashs/B-rolls déposés, **jump cuts conservés** (coupes de montage, pas des effets) |

**Double barrage (rendu)** : `caviarRender.js` VÉRIFIE le Budget d'Attention
du pack avant application — dépense > 55 u ou cap dépassé → les événements
excédentaires sont DÉPOSÉS (le plus cher puis le plus tardif d'abord, la
respiration gagne) et le gate passe ROUGE. Côté CI, `caviar_gate.py`
(rouge dure) vérifie le pack avant rendu ET le manifeste agrégé avant
publication du bundle final (budget PAR entrée). Miroir budget
`src/data/caviar_budget.json` diffé avec la source HEISENBERG à chaque rendu.

**Tests** : `npm run test:caviar` (21/21 — zéro dépendance externe) +
`test_caviar_gate.py` (14/14) + non-régression `test_heisenberg.py` (20/20)
et `test_caviar.py` Groupe 1 (vert). Zéro régression : bloc `caviar` absent
du pack = rendu historique à l'identique.

### 8.1 Contrat de pack — test en conditions réelles

Passthrough vérifié : le bloc `caviar` du pack survit à toute la chaîne
`parsePurPack` → `parsePurPackMulti` (bloc racine) → **par entrée** en
multi-vidéos → composition (`entry.caviar ?? manifest.caviar`). Miroirs
F03_PREVIEW/F03_PICTOR `bridgeClipper.js` diffé à chaque exécution des tests.

```json
"caviar": {
  "enabled": true,
  "source": "heisenberg",
  "jump_cuts":  [{ "cut_at_sec": 10.0, "removes_sec": 0.6 }],
  "punchins":   [{ "at_sec": 5.0, "scale_to": 1.08, "attack_frames": 3, "hold_frames": 6, "release_frames": 9 }],
  "brolls":     [{ "at_sec": 8.0, "numero": 1, "file": "broll/broll_01.mp4", "sfx": "impact", "duration_frames": 45 }],
  "smash_audio": [{ "at_sec": 20.0, "duck_db": -12, "duration_sec": 0.8 }]
}
```

- Bloc au niveau racine du pack (1 pack = 1 vidéo) ; en multi, CHAQUE pack
  porte ses décisions (budget vérifié PAR entrée au gate).
- `file` est résolu par le bras armé via le registre numéroté — le MP4 doit
  exister dans `F03_PICTOR/CODEBASE/public/broll/` (jamais commité). **Pas de
  fichier = pas de B-roll** (l'événement est déposé, le rendu reste propre).
- Jump cuts / punch-ins / smash fonctionnent SANS aucun asset — un premier
  test réel est possible avec un pack sans B-roll.
- SFX disponibles côté rendu : `impact` (`public/sfx/impact.mp3`).
- Le gate `caviar_gate.py` refuse le pack AVANT rendu si le bloc viole le
  Budget d'Attention — corriger le pack, pas la doctrine.
