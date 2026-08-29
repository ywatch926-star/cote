# LACRIMAE — CARNET DE BORD DE CAMPAGNE
> *"Les larmes de l'Ange ne tombent jamais en vain."*
> Croisade active : FORGE ALPHA | Magos : —

---

## ÉTAT DE LA FLOTTE

| Frégate | Nom | Statut | Date Scellage |
|---------|-----|--------|---------------|
| F01 | CANTOR | 🟢 SCELLÉE | 2026-05-19 |
| F02 | VISIO | 🟢 SCELLÉE | 2026-05-19 |
| F03 | PICTOR | 🟢 SCELLÉE | 2026-05-19 |
| F04 | SIGNUM | 🔵 EN TEST | — |
| — | LAC_CUSTOS | 🟢 SCELLÉE | 2026-05-19 |

**Légende :** ⚪ En attente | 🟡 En forge | 🔵 En test | 🟢 SCELLÉE | 🔴 BLOQUÉE

---

## FIL D'ARIANE

| Date | Frégate | Phase | Action | Validation |
|------|---------|-------|--------|------------|
| 2026-05-18 | FLOTTE | ALPHA | Cahier des charges V1 validé — brainstorming terminé | ✅ |
| 2026-05-18 | FLOTTE | ALPHA | Architecture 4 frégates validée — Lore Blood Angels appliqué | ✅ |
| 2026-05-18 | FLOTTE | ALPHA | Repo GitHub créé — documentation initiale poussée | ✅ |
| 2026-05-18 | FLOTTE | FORGE | Codebase complète forgée — F01, F02, F03, F04, LAC_CUSTOS | ✅ |
| 2026-05-19 | F01 | TEST PROD | Transcription Whisper medium — 26 mots, 8.59s, GPU T4 | ✅ |
| 2026-05-19 | F01 | TEST PROD | CUSTOS check-out F01 validé — timing.json 4068 octets | ✅ |
| 2026-05-19 | F01 | SCELLAGE | **F01 CANTOR SCELLÉE** — Transit F01→F02 autorisé | ✅ |
| 2026-05-19 | F02 | TEST PROD | creative_config.json validé — 30fps, 1080x1920, Cinzel+Playfair | ✅ |
| 2026-05-19 | F02 | SCELLAGE | **F02 VISIO SCELLÉE** — Transit F02→F03 autorisé | ✅ |
| 2026-05-19 | F03 | TEST PROD | Patch staticFile Remotion — assets binaires corrigés | ✅ |
| 2026-05-19 | F03 | TEST PROD | Rendu Remotion 258/258 frames — short_final.mp4 65.3 Mo | ✅ |
| 2026-05-19 | F03 | TEST PROD | CUSTOS check-out F03 validé — Transit F03→F04 autorisé | ✅ |
| 2026-05-19 | F03 | SCELLAGE | **F03 PICTOR SCELLÉE** — Ad Victoriam | ✅ |

---

## COMPTEUR DE GUERRE

```
Forge des Frégates : [███████░░░] 3/4 Frégates Scellées — F01 ✓ F02 ✓ F03 ✓
LAC_CUSTOS         : [██████████] SCELLÉE ✓
Fleet Seal         : [░░░░░░░░░░] En attente — F04 SIGNUM en test
Objectif           : Fleet Seal Certificate + 1er Short rendu
```

---

## ARCHITECTURE DE LA FLOTTE

```
[audio_clean.mp3 + images/]
         │
         ▼
[F01 CANTOR] ──► timing.json                            🟢 SCELLÉE
         │
         ▼
[F02 VISIO] ──► creative_config.json                    🟢 SCELLÉE
         │
         ▼
[F03 PICTOR] ──► short_final.mp4                        🟢 SCELLÉE
         │
         ▼
[F04 SIGNUM] ──► short_master.mp4                       🔵 EN TEST
```

---

## FRÉGATE F01 — CANTOR 🟢 SCELLÉE

### Composants Forgés
- ✅ `LAC_F01.ipynb` — Notebook Colab (7 étapes validées)
- ✅ `lac_f01_cantor.py` — faster-whisper + STRONG_WORDS + validation interne
- ✅ `README_DEV.md`

### Résultats Test Production
- Audio : `audio_clean.mp3` — 8.5914s
- Mots transcrits : 26 | FPS : 30 | Frames : 258
- Modèle Whisper : medium | Device : CUDA float16
- Mot fort détecté : "night" (is_strong: true)
- CUSTOS check-out : ✅ VALIDÉ — 4068 octets

### Inputs / Outputs
```
IN/audio_clean.mp3  →  OUT/timing.json  ✅
```

---

## FRÉGATE F02 — VISIO 🟢 SCELLÉE

### Composants Forgés
- ✅ `LAC_F02.ipynb` — Notebook Colab (8 étapes)
- ✅ `lac_f02_flask.py` — Flask 6 endpoints REST
- ✅ `lac_f02_viewer.html` — Viewer HTML (timeline, phone preview, sliders)
- ✅ `README_DEV.md`

### Résultats Test Production
- creative_config.json : 30fps, 1080x1920, Cinzel + Playfair Display
- cut_interval_frames : 7 | grain_overlay_opacity : 0.30
- CUSTOS check-out : ✅ VALIDÉ

### Inputs / Outputs
```
IN/timing.json + IN/images/  →  OUT/creative_config.json  ✅
```

---

## FRÉGATE F03 — PICTOR 🟢 SCELLÉE

### Composants Forgés
- ✅ `LAC_F03.ipynb` — Notebook Colab (10 étapes + patch staticFile)
- ✅ `src/index.jsx` — Entry point Remotion
- ✅ `src/Root.jsx` — Composition template
- ✅ `src/components/LacrimaeShort.jsx` — Composant principal
- ✅ `src/package.json` — Dépendances npm
- ✅ `README_DEV.md`

### Résultats Test Production
- 258 frames rendues @ 30fps — Remotion v4.0.463
- Sortie : short_final.mp4 — 65.3 Mo — 1080x1920
- Codec : h264 / AAC
- Patch appliqué : assets binaires → staticFile() + dossier public/
- Frame la plus lente : Frame 88 (1222ms)
- CUSTOS check-out : ✅ VALIDÉ — 65325374 octets

### Inputs / Outputs
```
IN/ (timing + config + audio + images)  →  OUT/short_final.mp4  ✅
```

---

## FRÉGATE F04 — SIGNUM 🔵 EN TEST

### Composants Forgés
- 🔵 `LAC_F04.ipynb` — Notebook Colab (8 étapes + download)
- 🔵 `lac_f04_signum.py` — FFmpeg remux + vérif durée + métadonnées + faststart
- 🔵 `README_DEV.md`

### Inputs / Outputs
```
IN/short_final.mp4 + IN/timing.json  →  OUT/short_master.mp4
```

---

## NOTES DE FORGE

### 2026-05-18 — Séance de Fondation
Architecture validée. Décisions actées :
- Audio séparé fourni directement par le Magos (pas de Demucs en V1)
- Port Colab natif — pas de ngrok
- Images 1:1 : object-fit cover (cadrage auto)
- Durée vidéo = durée audio_clean.mp3
- Fast cut : 6-8 frames (ajustable dans VISIO)
- Lore Blood Angels. Projet : LACRIMAE.

### 2026-05-18 — Forge Alpha
Codebase complète forgée :
- F01 CANTOR, F02 VISIO, F03 PICTOR, F04 SIGNUM, LAC_CUSTOS
- Prochaine étape : tests sur Colab avec audio et images réels

### 2026-05-19 — Test de Production V1
F01, F02, F03 scellées. Trois frégates validées en un seul jour.
- Patch staticFile appliqué sur F03 (assets binaires webpack)
- .webp retiré de toutes les frégates (jpg/jpeg/png uniquement)
- short_final.mp4 : 65.3 Mo, 258 frames, h264/AAC, 1080x1920
- F04 SIGNUM : en test — Fleet Seal imminent.
- Que l'Empereur protège son output.

---

## PRINCIPES — LES RITES DU SANG

1. **LOI D'ISOLEMENT** — Chaque frégate est une île. Aucun accès croisé.
2. **RITE DE VALIDATION** — LAC_CUSTOS obligatoire avant chaque transit.
3. **GRATUITÉ ABSOLUE** — 0€ de coût opérationnel.
4. **CHECKPOINT SACRÉ** — F03 PICTOR est toujours récupérable après interruption.
5. **TRANSIT MANUEL** — Le Magos déplace les fichiers. Jamais les scripts.
6. **DURÉE PAR L'AUDIO** — La durée de la vidéo est dictée par l'audio. Toujours.


## 2026-08-22 — Forge dev4 : phase 1

- F00 INGEST ajouté : manifeste de séquences virtuelles, sans extraction de clips.
- F03_PREVIEW raccordé à `sequences.json` et à la lecture muette des séquences.
- F03_PICTOR aligné sur la composition Remotion de la preview ; ancien Root Colab conservé comme référence legacy.
- Workflow `.github/workflows/dev4_pipeline.yml` ajouté avec skip explicite de F01 et F02.
- Vérifications : F00 OK, build Vite OK, rendu PICTOR OK sur vidéo synthétique.
- Rapport : `TRACKING/DEV4_PHASE1_REPORT.md`.


## 2026-08-22 — Dev4 terminé

Le flux F00 → F03_PREVIEW → F03_PICTOR est opérationnel sur les contrats virtuels. F01 et F02 sont contournables par paramètres explicites dans le workflow GitHub Actions. Tests F00, validation JSON, build Vite, parité de composition et rendu Remotion validés. Rapport final : `TRACKING/DEV4_FINAL_REPORT.md`.
