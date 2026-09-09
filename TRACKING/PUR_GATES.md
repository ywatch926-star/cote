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
| **G1 VOD** | Téléchargement | Segment VOD obtenu | yt-dlp OK, fichier produit, ≤ 300 s de download |
| **G2 DUREE** | Après download | Durée du clip | `duration == end_sec − start_sec ± 0.5 s` |
| **G3 CODEC** | Après download | Lisibilité | codec ∈ {h264, vp9, hevc, av1}, dimensions > 0 |
| **P0 MANIFESTE** | Après conversion | `pur_manifest.json` valide | `schema_version=dev10.pur.v1`, ≥ 1 entrée, overlay non vide |
| **P1 PREVIEW** | Avant rendu | Validation visuelle F03 | Hook 0-3 s sans texte, overlay lisible, anti-détection conforme au pack |
| **P2 RENDU** | CI | MP4 produit | Résolution du canvas choisi, durée ≈ manifeste, artefact uploadé |

## Politique d'échec

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
