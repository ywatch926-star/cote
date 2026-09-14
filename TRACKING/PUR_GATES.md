# LACRIMAE dev10 — PUR GATES DE VALIDATION

## Doctrine

dev10 est le **bras armé du mode PUR** de PERTURABO. Le monde forge
`MONDES_FORGES/CLIPPING` analyse, score et écrit ; dev10 exécute : il
récupère le pack, télécharge le segment vidéo réel, convertit les
instructions en rendu et produit le MP4 final.

```
PERTURABO EXPORT/production_pack_pur_*.json
        │
        ▼
[BRIDGE mode --pur]  fetch + G0 + conversion → pur_manifest.json
        │
        ▼
[F00-PUR f00_pur.py]  yt-dlp --download-sections → clips/pur_<angle>.mp4
        │
        ▼
[F03 Preview onglet ⚡ PUR]  validation visuelle (canvas, overlay, anti-détection)
        │
        ▼
[F04 Render — GitHub Actions dev10_pur_render.yml]  Remotion → lac_pur_final.mp4
        │
        ▼
[Journalisation TRACKING/PUR_CAMPAIGN_LOG.md]
```

## Gates

| Gate | Moment | Vérification | Critère de passage |
|---|---|---|---|
| **G0 PACK** | Avant tout | Pack PUR exploitable | `mode=pur`, `vod_url` présente, `start_sec < end_sec`, segment ≤ 150 s, `montage_instructions` présente |
| **G0-S STYLE** | Conversion | Style de montage identifié ET autorisé | `montage_style` (racine pack) ou `metadata.style` ∈ {ranking, reframing, blur, split_scene}, **OU** choix explicite opérateur (`--style`). Style inféré seul ou inconnu → **REFUSÉ (exit 2), rendu bloqué** — règle du 2026-09-09 : c'est l'opérateur qui choisit, jamais le code en silence |
| **G1 VOD** | Téléchargement | Segment VOD obtenu | yt-dlp OK, fichier produit, ≤ 300 s de download |
| **G2 DUREE** | Après download | Durée du clip | `duration == end_sec − start_sec ± 0.5 s` |
| **G3 CODEC** | Après download | Lisibilité | codec ∈ {h264, vp9, hevc, av1}, dimensions > 0 |
| **P0 MANIFESTE** | Après conversion | `pur_manifest.json` valide | `schema_version=dev10.pur.v1`, ≥ 1 entrée, overlay non vide, `style` ∈ les 4 valeurs avec `style_source` ∈ {pack, operator} |
| **P-AGG MULTI** | Après les N rendus matrix | `tools/pur_aggregate.py` | Chaque entrée du codex multi-vidéos a son MP4 lisible. **Un seul manque → publication refusée** (aucun bundle incomplet, jamais). Bundle final = `lac-pur-final` (N MP4 distincts + manifestes + rapport) — zéro concat, prêt pour F05 `--batch`. (2026-09-10) Leçon du 2026-09-11 : l'identité d'entrée est `source_id`, préfixé (`pur_<angle>`) — l'agrégateur la normalise via `normalize_angle()` (commit `ba979c2`) ; la recherche reste `pur_<angle>_finale.mp4`.
| **P1 PREVIEW** | Avant rendu | Validation visuelle F03 | Overlay lisible (1 ligne = 1 ligne visuelle, max 3), texte statique du début à la fin (règle « hook sans texte » ABROGÉE le 2026-09-10), auto-fit 1 ligne = 1 ligne visuelle (max 3) — **implémenté le 2026-09-10**, anti-détection conforme au pack. Panneaux opérateur (texte, style, anti-détection) — réglages dans `style_params` |
| **P2 RENDU** | CI | MP4 produit | Résolution du canvas choisi, durée ≈ manifeste, artefact uploadé |
| **P-AUD AUDIO** | Agrégation | Piste audio du MP4 | `audio_codec` présent (ffprobe) — un rendu muet est refusé comme un rendu manquant (2026-09-11, décision Warsmith : voix du clip ON, codex « voix claire » hook) |
| **P-CAV CAVIAR** | F00-PUR, après G0 | Budgets narratifs du pack | `caviar.gate_pcav_budgets()` — champs narratifs PRÉSENTS mais invalides = rouge (job stoppé) ; absents = bypass. Constantes miroir de `F03_PICTOR/HEISENBERG/caviar_budget.json` (2026-09-13, Groupe 1) |
| **H-CAV HEISENBERG** | Après agrégation | Analyse des MP4 finis | `F03_PICTOR/HEISENBERG/heisenberg.py --batch` — émet un `caviar_manifest_<stem>.json` par vidéo finale (verdicts OK/BLOCKED/REFUSED, Budget d'Attention, B-roll numéroté). **Advisory** : un échec ne bloque pas la livraison ; verdict REFUSED (« segment mauvais ») journalisé comme avertissement opérateur (2026-09-14, Groupe 2) |
| **P-ENGIN MOTEUR UNIQUE** | Build CI | Code de rendu PUR | PICTOR importe le moteur validé de la preview (`_purPackComposition` + `bridgeClipper` + `antiDetection`) — **aucune copie du moteur PUR dans PICTOR** (décision Warsmith 2026-09-11). Les doublons `_purPackComposition.jsx`/`purPackCompilation.js` de PICTOR sont supprimés. Le re-routage ranking (`buildRankingFromPur`) qui masquait le moteur PUR est supprimé — cause racine des rendus non conformes au codex (zooms, blur, SFX absents) |

## Politique d'échec

- **G0-S échoue → RENDU BLOQUÉ.** L'écran de rendu affiche « ⏸ RENDU BLOQUÉ — STYLE PUR » avec la marche à suivre. Deux sorties : (1) regénérer le pack côté PERTURABO avec `--style`, (2) relancer la conversion avec `--style ranking|reframing|blur|split_scene` — choix de l'opérateur, jamais du code.
- G0 échoue → le pack retourne à PERTURABO (F06_DIRECTOR) — jamais de correction manuelle côté dev10.
- G1/G2/G3 échouent → VOD expirée ou privée : basculer le clip en asset GitHub Release (pattern dev9 Spider-Man) et rejouer.
- P1 échoue → corriger dans le preview (overlay, canvas), re-valider avant rendu.

## Contrats à préserver

| Contrat | Chemin | Propriétaire |
|---|---|---|
| Pack PUR v2.0.0-viral | `production_pack_pur_*.json` (PERTURABO EXPORT) | PERTURABO F06_DIRECTOR |
| Manifeste dev10.pur.v1 | `BRIDGE_PERTURABO/OUT/pur_manifest.json` → `F03_PREVIEW/CODEBASE/public/` + `F03_PICTOR/CODEBASE/public/` | dev10 bridgeClipper.js |
| Sources segment | `F03_PICTOR/CODEBASE/public/clips/pur_sources.json` | F00-PUR |
| Parité preview/render | `_purPackComposition.jsx` (F03) ↔ `_purPackComposition.jsx` (F04) | dev10 |
| Paramètres opérateur | `style_params` (racine = style, `narrative.overlay.style_params` = texte) dans `dev10.pur.v1` | dev10 — défauts dans `PUR_STYLE_PARAMS_DEFAULTS` / `PUR_OVERLAY_DEFAULTS` (miroir F03 `bridgeClipper.js` ↔ F04 `purPackCompilation.js`) |
