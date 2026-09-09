# Guide Opérateur — Le Bras Armé PUR (PERTURABO → LACRIMAE dev10)

> Pour le Warsmith qui veut transformer un pack PUR en vidéo publiée.
> Pas besoin de connaître le code. Suivez les étapes.

---

## Le principe en 3 lignes

1. **PERTURABO** (MONDES_FORGES/CLIPPING) analyse une VOD et exporte un
   `production_pack_pur_*.json` dans `EXPORT/` — le pack contient le
   segment (vod_url + secondes), le copywriting (overlay 2 lignes) et les
   instructions de montage (hook, zooms, anti-détection).
2. **LACRIMAE dev10** exécute : le bridge convertit le pack, F00-PUR
   télécharge le vrai segment vidéo, le preview permet la validation,
   GitHub Actions rend le MP4.
3. Tu ne fais qu'appuyer sur les portes : jamais la VOD complète, jamais
   de modification du pack côté dev10.

---

## Checklist rapide

- [ ] Pack PUR récent dans `PERTURABO/MONDES_FORGES/CLIPPING/EXPORT/`
- [ ] VOD source joignable (Twitch publique, `source_permission: campaign_provided`)
- [ ] Choix du canvas (9:16 par défaut pour Shorts/TikTok)

---

## Étape 1 — Bridge : récupérer + convertir le pack

```bash
python3 BRIDGE_PERTURABO/CODEBASE/lac_bridge_forge.py --pur --pack-filter pur_A01
```

Le bridge va chercher SEUL le pack dans EXPORT PERTURABO, valide le gate
G0, convertit en `pur_manifest.json` (dev10.pur.v1) et le transite vers
`F03_PREVIEW/CODEBASE/public/` et `F03_PICTOR/CODEBASE/public/`.

Variante manuelle (pack déjà téléchargé) :

```bash
python3 BRIDGE_PERTURABO/CODEBASE/lac_bridge_forge.py --pur \
  --pack /chemin/production_pack_pur_A01.json
```

---

## Étape 2 — F00-PUR : télécharger le segment vidéo réel

```bash
python3 F00_INGEST/CODEBASE/f00_pur.py \
  --pack BRIDGE_PERTURABO/IN/production_pack_pur_A01.json \
  --out F03_PICTOR/CODEBASE/public/clips
```

Gates automatiques : G0 (pack), G1 (VOD), G2 (durée ±0.5 s), G3 (codec).
Résultat : `clips/pur_A01.mp4` + `clips/pur_sources.json`.

---

## Étape 3 — Preview : validation visuelle (gate P1)

Lancer F03 Preview (Vite), ouvrir l'onglet **⚡ PUR** :

- Déposer le `production_pack_pur_A01.json` → conversion instantanée.
- Vérifier : hook 0-3 s (visage du speaker, PAS de texte), overlay
  2 lignes après le hook, zooms frame-exacts, mirror/speed/crop.
- Le canvas 9:16 / 16:9 / 1:1 est switchable en direct.
- L'overlay est éditable avant validation (corrections mineures OK ;
  corrections de fond → retour PERTURABO).

---

## Étape 4 — Rendu CI (gate P2)

GitHub Actions → **DEV10 PUR — Bras armé PERTURABO** → Run workflow :

| Input | Valeur | Rôle |
|---|---|---|
| `pack_filter` | `pur_A01` | quel pack rendre |
| `canvas` | `9:16` | format de sortie |
| `perturabo_branch` | `main` | branche PERTURABO à lire |
| `max_duration` | `0` | durée complète (ou nb de secondes pour test rapide) |

Le workflow fait TOUT : fetch pack → F00-PUR → conversion → injection
codex → Remotion render → artefacts `lac-pur-final-*` (MP4) et
`lac-pur-manifests-*` (traçabilité).

---

## Étape 5 — Journaliser + canoniser

1. Télécharger l'artefact MP4, contrôle visuel (0 s / 2.9 s / 3.1 s /
   zoom / fade final).
2. Ajouter une ligne dans `TRACKING/PUR_CAMPAIGN_LOG.md`.
3. Si c'est le premier E2E validé : tag `pur-canon-v1`.

---

## En cas de problème

| Symptôme | Cause probable | Action |
|---|---|---|
| G0 échoue | pack incomplet | retour PERTURABO F06_DIRECTOR |
| G1 échoue | VOD expirée / privée | uploader le clip en Release GitHub (pattern dev9), rejouer |
| G2 échoue | dérive de timestamps | vérifier start/end_sec du pack |
| `CLIP PUR MANQUANT` au preview | F00-PUR pas lancé | exécuter l'étape 2 |
| Rendu CI échoue | voir `freebuff`-logs du run | vérifier pur_manifest injecté + clips/ présents |

---

## Rappels doctrine PUR (à ne jamais violer)

- Jamais de texte pendant le hook (0-3 s) — visage du speaker uniquement.
- Jamais de clip sans anti-détection (mirror + 1 SFX minimum).
- SFX toujours sous la voix (−6 à −20 dB).
- Pas de CTA — finir sur la chute (fade_to_black).
