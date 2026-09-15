# CAVIAR PACK V2 — contrat pack v2 + partition F00D (côté bras armé)

> **Source de vérité** : note technique PERTURABO → bras armé, 2026-09-15
> (dépôt `jfbjfojfonf/PERTURABO`). Ce guide décrit comment dev10 la reçoit et
> l'exécute. **Rappel doctrinal** : F00D commande le geste, F06 exécute le
> reste, le bras armé rend, le gate vérifie — personne ne crée.

**Statut (2026-09-15)** : Groupe 1 v2 implémenté et vérifié sur le pack RÉEL
`production_pack_pur_voxc2_blur_v2.json` (voxc-2). Groupe 2 (rendu du panneau
possédé par la partition) en attente de GO.

---

## 1. Le pack arrive — canal et pièges

- **Canal unique** : dépôt PERTURABO, branche `v2-live-vox-c`,
  `MONDES_FORGES/CLIPPING/EXPORT/production_pack_<campagne>_<candidat>_<style>_v2.json`.
- **Piège historique** : `OUT/` des frégates est gitignoré — un pack cherché
  dans OUT/ via raw URL donne un 404. Toujours passer par EXPORT/ ou
  `packs_index.json`.
- **Immutabilité** : le pack est immuable après validation. Toute modification
  de source/réaction/motion/tag/chaîne = nouveau passage de gate.
- **Porte d'entrée** : n'exécuter que si
  `review.gate_state == "ALL_GATES_GO"` **ET** `review.status == "VALIDATED"`.
  `status: DRAFT` ≠ exécutable.

## 2. Détection de version (jamais d'échec sur vieilles clés)

La détection se fait par **présence** de blocs, jamais par l'absence des
vieilles clés (`angle`, `cut_directives`, `reference_style`, `text_payload`,
`submission_checklist`) :

| Schéma | Signature | Traitement |
|---|---|---|
| **v2** | `caviar_partition` (objet) | `caviarV2.js` : normalisation → moteur |
| **v1** | `caviar` (objet) | moteur direct (Groupe 3) |
| **v0** | aucun des deux | rendu historique à l'identique |

## 3. Le mapping v2 → moteur (`src/caviarV2.js`)

| Partition F00D (v2) | Moteur (v1) | Notes |
|---|---|---|
| `panels[]` (et `events.broll[]` au manifeste) | `brolls[]` | `start_sec` → `at_sec` ; `broll_id` résolu par le registre ; `crop_zoom`, `blur_radius_px`, `panel`, `emotion_requested` transportés dans `extra` |
| `silence_trims[]` | `jump_cuts[]` | `cut_at_sec`/`start_sec`, `removes_sec`/`duration_sec` |
| `events.punch_ins[]` (ou top-level) | `punchins[]` | `crop_zoom` → `scale_to` |
| `smash_audio[]` (top **ou** `events.`) | `smash_audio[]` | tel quel |
| `bound: true` | `enabled: true` | |
| `resolution_at`, `run_id`, `budget_state` | `extra` | consommés par le gate |

**Tolérance documentée (vérifiée sur voxc-2)** : le pack réel porte
`panels[]` et `smash_audio[]` au **top** de la partition, le manifeste
`caviar.v1` les décrit sous `events.*` — les deux formes sont acceptées.

## 4. Le registre sémantique (broll_id → fichier)

- Index `semantic` : `"BLUR-01" → { file, sfx, entry_flash, emotions, duration_frames_max }`.
- **Compat v1** : un `broll_id` purement numérique (`"1"`) résout via `clips`.
- F00D/PERTURABO ne voient **jamais** les fichiers. Remplacer un asset =
  zéro modification du manifeste/pack.
- Assets non commités : `F03_PICTOR/CODEBASE/public/broll/` (rendu) et
  `HEISENBERG/BROLL/FILES/` (bibliothèque).
- **Pas de fichier résolu = pas de B-roll** : l'événement est déposé au rendu,
  le gate émet un avertissement, le rendu reste propre.

## 5. Les portes v2 du gate (`caviar_gate.py --pack-v2 <pack.json>`)

| Porte | Vérification | Rouge si |
|---|---|---|
| **review** | `ALL_GATES_GO` + `VALIDATED` | DRAFT / PENDING → refus sans rendu |
| **caviar_bound** | `f06_gate.mode` commence par `caviar_bound` | mode legacy |
| **hiérarchie** | partition présente → `body.cuts[]`/`zooms[]` DOIVENT être vides | F06 produit ses propres cuts/zooms (régression) |
| **checksum16** | binding == custody (interne) ; avec `--manifest-caviar` : sha256_16 du manifeste livré == binding | divergence → refuse le rendu |
| **horodatage** | `run_id` du manifeste < `generated_at` du pack | manifeste après pack |
| **resolution_at** | aucun `panels`/`punch_ins`/`smash_audio` après | événement tardif (note §3.5) |
| **budget croisé** | dépense RECALCULÉE ≤ 55 u, `caps_respected != false`, `spent_units` == recalcul | pack mensonger |

Dans la CI (`dev10_pur_render.yml`), l'étape gate tente de récupérer le
manifeste F00D déclaré dans `chain_of_custody.f00d_partition.manifest`
(best-effort, non bloquant si introuvable : la partition embarquée fait foi,
checksum marqué « non vérifié »).

## 6. La hiérarchie — à ne pas inverser

- **caviar_owned** (la partition commande) : cuts, zooms, sfx_events, mirror,
  speed, crop, panel_render, audio_duck.
- **F06 fournit en complément** : texte, courbe d'énergie recalée,
  anti-détection complémentaire (sfx_background_layer, color_shift, trim),
  compliance.
- Si `body.cuts[]`/`zooms[]` sont vides : **c'est normal** — le geste est dans
  `caviar_partition`. Ne pas croire à un pack incomplet.

## 7. Vérifié sur le pack réel (voxc-2, style blur)

- Portes v2 : **vertes** (review GO ×5, caviar_bound v3.0.0, hiérarchie ok,
  checksums internes cohérents `65bef6ba008af8e2`, manifeste avant pack,
  aucun événement après `resolution_at: 41.041s`).
- Budget : **32u recalculées == 32u déclarées** (2 panels × 12 + 1 smash × 8),
  respiration 68u, caps respectés.
- Mapping : BLUR-01 @12.825s + BLUR-02 @25.651s (36 frames, flash entrée,
  SFX impact), smash @28.216s −12 dB/0.8s — flashs posés aux bons frames
  même à `speed: 1.05`.
- Tests : adaptateur v2 **12/12**, gate **24/24**, moteur **21/21**.

## 8. Ce qui reste (Groupe 2 — après GO opérateur)

1. **Rendu du panneau possédé par la partition** : appliquer `crop_zoom`
   (1.3), `blur_radius_px` (18) et `panel: vertical_text_overlay` au B-roll
   rendu (aujourd'hui : overlay plein cadre simple).
2. **Rendu réel de bout en bout** sur voxc-2 (ou pack équivalent) : jump cuts
   (0 dans ce pack), punch-ins (0), smash (exporté, s'activera avec la piste
   musicale), panels B-roll dès que les MP4 `BLUR-01/02` sont déposés dans
   `public/broll/`.
