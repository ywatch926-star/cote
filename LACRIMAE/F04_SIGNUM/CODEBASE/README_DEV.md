# F04 SIGNUM — README DÉVELOPPEUR
> *"Le Sceau est apposé. La vidéo devient artefact livrable."*

---

## Mission

Finalisation FFmpeg : remux propre, injection de métadonnées, vérification que la durée de la vidéo correspond à la durée de l'audio source (LOI DURÉE PAR L'AUDIO), optimisation moov atom pour web (faststart).

---

## Technologie

| Composant | Version cible |
|-----------|---------------|
| FFmpeg | ≥ 6.0 (disponible sur Colab) |
| ffprobe | Inclus avec FFmpeg |
| Python | 3.10+ (stdlib uniquement pour la logique, subprocess pour FFmpeg) |

---

## Fichiers

| Fichier | Rôle |
|---------|------|
| `LAC_F04.ipynb` | Notebook Colab — point d'entrée opérateur |
| `lac_f04_signum.py` | Script principal FFmpeg finalisation |
| `README_DEV.md` | Ce fichier |

---

## Inputs / Outputs

```
IN/
├── short_final.mp4     ← De F03 PICTOR (transit manuel)
└── timing.json         ← De F01 CANTOR (transit manuel) — source de vérité durée

OUT/
└── short_master.mp4    ← Livrable final téléchargeable par le Magos
```

---

## Pipeline FFmpeg

```
short_final.mp4 (input)
    │
    ├── ffprobe → vérification durée vs timing.json
    │
    └── ffmpeg -c copy               (stream copy — pas de re-encodage)
              -metadata title=...
              -metadata artist=LACRIMAE
              -movflags faststart     (moov atom en tête pour web)
              → short_master.mp4
```

**Important** : `-c copy` signifie zéro perte de qualité — uniquement un remux.

---

## Vérification durée

La durée réelle de `short_final.mp4` est comparée à `timing.audio_duration_s`.
Tolérance : ±2 frames. Un avertissement est émis si l'écart dépasse la tolérance, mais le processing continue (Remotion peut introduire 1-2 frames de marge).

---

## Rites du Sang applicables

- **LOI D'ISOLEMENT** : SIGNUM ne lit que `F04/IN/`. Aucun accès aux autres frégates.
- **DURÉE PAR L'AUDIO** : Vérification obligatoire écart durée ≤ 2 frames.
- **RITE DE VALIDATION** : LAC_CUSTOS check-in avant traitement, check-out avant livraison.
