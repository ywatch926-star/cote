# LACRIMAE dev10 — PUR : Historique d'implémentation

## Date : 9 septembre 2026

## Résumé

dev10 est canonisé **bras armé du mode PUR** de PERTURABO : le monde forge
`MONDES_FORGES/CLIPPING` produit les `production_pack_pur_*.json`, dev10 les
exécute de bout en bout (VOD réelle → MP4), 100 % GitHub Actions, zéro Modal.

## Timeline

### 2026-09-09 — Lot 1 : contrat + ingest (42a9ebc)
- `bridgeClipper.js` v2 : `parsePurPack()` consomme les packs v2.0.0-viral
  (copywriting.overlay_title en fallback du legacy text_payload, zooms
  frame-exacts depuis body.zooms, anti-détection réelle depuis
  anti_detection.techniques, canvas adaptatif 9:16/16:9/1:1).
- `F00_INGEST/CODEBASE/f00_pur.py` : téléchargement du segment VOD réel via
  `yt-dlp --download-sections` (doctrine F00B_VOX : jamais la VOD complète),
  gates G0/G1/G2/G3, sortie `pur_sources.json` + `clips/pur_<angle>.mp4`.
- Fixtures réelles : packs A01/A02/A03 du jour (VOD Twitch 2864600351).
- Tests : 37 checks Node + 10 pytest verts. Test réel : segment Twitch 30 s
  téléchargé (H.264 1920x1080, 30.2 s), gates G0-G3 PASSED.

### 2026-09-09 — Lot 2 : preview + rendu + CI (61b719f)
- F03 Preview : onglet ⚡ PUR (upload pack → conversion navigateur via
  parsePurPack, canvas switchable, overlay éditable, infos anti-détection).
- `PurPackComposition` : clip plein écran, hook 0-3 s sans texte (doctrine
  PUR), overlay pop_in après le hook, zooms brutal_impact/snap_zoom,
  mirror + breathing zoom + crop + speed, outro fade_to_black.
- F04 PICTOR : `purPackCompilation.js` + miroir exact du composant (parité
  doctrine dev9), `Root.jsx` route `pur_pack`, durée depuis pur_manifest.
- CI : `dev10_pur_render.yml` (pattern dev9_ranking_render) : fetch pack
  EXPORT → F00-PUR → convert CLI (`tools/convert_pur_pack.mjs`) → injection
  codex → remotion render → artefacts MP4 + manifestes.

### 2026-09-09 — Lot 3 : bridge + docs + E2E
- `lac_bridge_forge.py` : chemins corrigés (F02_VISIO / F04_SIGNUM au lieu
  des F02_FORMAT / F04_RENDER hérités), `--pur` : fetch pack + G0 +
  conversion manifeste + transit F03/F04 public.
- Docs : PUR_GATES.md, PUR_CAMPAIGN_LOG.md, PUR_IMPLEMENTATION.md,
  GUIDE_BRAS_ARME_PUR.md, TODO_CONTINUATION.md réécrit pour dev10.

## Commandes de référence

```bash
# 1. Bridge mode PUR (fetch + conversion)
python3 BRIDGE_PERTURABO/CODEBASE/lac_bridge_forge.py --pur --pack-filter pur_A01

# 2. Ingest segment VOD réel
python3 F00_INGEST/CODEBASE/f00_pur.py --pack BRIDGE_PERTURABO/IN/production_pack_pur_A01.json --out F03_PICTOR/CODEBASE/public/clips

# 3. Rendu complet (CI) : GitHub Actions → DEV10 PUR — Bras armé PERTURABO
#    inputs : pack_filter=pur_A01, canvas=9:16
```

## Règles de reprise

Travailler sur `dev10` (ou branche dérivée `dev10-pur`), lire ce fichier,
`TRACKING/PUR_GATES.md` et `TRACKING/TODO_CONTINUATION.md`. Ne jamais
modifier un pack PUR côté dev10 — les corrections remontent à PERTURABO.
Chaque gate doit être journalisé dans `PUR_CAMPAIGN_LOG.md`.
