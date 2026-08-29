# F01 CANTOR — README DÉVELOPPEUR
> *"Le Chantre transcrit. La mémoire de l'Ange devient données."*

---

## Mission

Transcrire `audio_clean.mp3` via faster-whisper et produire `timing.json` — le fichier de référence temporelle mot par mot pour toute la flotte.

---

## Technologie

| Composant | Version cible |
|-----------|---------------|
| Python | 3.10+ |
| faster-whisper | ≥ 1.0.0 |
| Modèle Whisper | `medium` (par défaut) — `large-v2` pour plus de précision |
| Device | CUDA (GPU T4 Colab) |

---

## Fichiers

| Fichier | Rôle |
|---------|------|
| `LAC_F01.ipynb` | Notebook Colab — point d'entrée opérateur |
| `lac_f01_cantor.py` | Script principal transcription |
| `README_DEV.md` | Ce fichier |

---

## Inputs / Outputs

```
IN/
└── audio_clean.mp3     ← Copié depuis SHARED/ par le Magos (transit manuel)

OUT/
└── timing.json         ← Produit par ce script
```

---

## Format timing.json

```json
{
  "audio_duration_s": 42.5,
  "total_frames": 1275,
  "fps": 30,
  "words": [
    {
      "word": "L'amour",
      "start_s": 1.24,
      "end_s": 1.67,
      "start_frame": 37,
      "end_frame": 50,
      "is_strong": false
    },
    {
      "word": "silence",
      "start_s": 2.10,
      "end_s": 2.80,
      "start_frame": 63,
      "end_frame": 84,
      "is_strong": true
    }
  ]
}
```

**Champs :**
- `audio_duration_s` — durée exacte de l'audio source (dicte la durée de la vidéo finale)
- `total_frames` — `ceil(audio_duration_s * fps)`
- `fps` — toujours 30
- `words[].word` — mot original (avec ponctuation)
- `words[].start_s / end_s` — timestamps en secondes (4 décimales)
- `words[].start_frame / end_frame` — frames correspondantes
- `words[].is_strong` — booléen — si `true`, rendu en `Playfair Display Italic` dans F03

---

## Utilisation dans Colab

Voir `LAC_F01.ipynb`. Séquence standard :

```
1. Monter Drive
2. Vérifier audio_clean.mp3 présent dans SHARED/
3. Lancer toutes les cellules
4. Vérifier OUT/timing.json produit
5. Lancer LAC_CUSTOS --frigate F01 --mode check-out
```

---

## Paramètres ajustables

### Taille du modèle (`model_size`)
| Modèle | Précision | Vitesse | Recommandé |
|--------|-----------|---------|------------|
| `tiny` | Faible | Très rapide | Tests rapides |
| `medium` | Bonne | Moyen | **Production standard** |
| `large-v2` | Excellente | Lent | Textes complexes/poétiques |

### Mots forts (`STRONG_WORDS`)
Liste dans `lac_f01_cantor.py`. A enrichir selon le registre de chaque campagne.

---

## Rites du Sang applicables

- **LOI D'ISOLEMENT** : CANTOR ne lit que `SHARED/audio_clean.mp3`. Aucune dépendance à d'autres frégates.
- **DURÉE PAR L'AUDIO** : `audio_duration_s` du timing.json est la source de vérité absolue pour la durée de la vidéo.
- **RITE DE VALIDATION** : Toujours valider avec `LAC_CUSTOS --frigate F01 --mode check-out` avant tout transit.
