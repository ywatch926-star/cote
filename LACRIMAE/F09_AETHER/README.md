# F09 AETHER COMPOSITUM — Compositing multicouche FFmpeg

## Objectif

Reproduire la logique After Effects (cc2.ffx) de manière headless via FFmpeg. Chaque preset est une configuration JSON avec des couches activables, des opacités contrôlées et des garde-fous contre les halos et les noirs bouchés.

## Presets disponibles

| Preset | Description | Couches |
|---|---|---|
| `clean_realistic` | Effet minimal, naturel préservé | 5 couches |
| `silver_gray` | Désaturation métallique, tons froids | 6 couches |
| `dark` | Contraste cinématique, noirs profonds | 6 couches |
| `warm` | Tons chair protégés, chaleur douce | 6 couches |
| `viral_hdr` | Impact HDR, glow, énergie | 6 couches |

## Architecture des presets

Chaque preset est un fichier JSON dans `PRESETS/compositing_presets.json` avec :

- **layers** : liste ordonnée de couches de filtres FFmpeg
  - `id` : identifiant unique
  - `effect` : effet After Effects équivalent
  - `enabled` : activé/désactivé
  - `opacity` : opacité 0.0–1.0 (interpolation entre identity et valeur complète)
  - `ffmpeg_filter` : filtre FFmpeg brut
  - `notes` : explication du rôle
- **global** : paramètres d'encodage (codec, crf, preset, pix_fmt, movflags)

## Mapping After Effects → FFmpeg

| Effet AE | Filtre FFmpeg | Rôle |
|---|---|---|
| ADBE Sharpen | `unsharp` | Netteté de base |
| ADBE Unsharp Mask2 | `unsharp` (params séparés) | Masque flou contrôlé |
| MB LookSuite3 | `curves` + `eq` + `colorbalance` | Look et colorimétrie |
| S_Gradient | `curves` (lift/gamma/gain) | Overlay de luminance |
| Grain custom | `noise` | Texture organique |

## Commandes

```bash
# Lister les presets
python3 F09_AETHER/CODEBASE/lac_f09_aether.py --list-presets

# Appliquer clean_realistic
python3 F09_AETHER/CODEBASE/lac_f09_aether.py \
  --input VIDEO/source.mp4 \
  --output F09_AETHER/OUT \
  --preset clean_realistic
```

## Sorties

```
F09_AETHER/OUT/
├── aether_clean_realistic.mp4
└── aether_report.json
```

## Intégration pipeline

F09 s'exécute **localement** (pas de GPU) entre F08 et F10 :
```
F08_TEMPORALIS → F09_AETHER_COMPOSITUM → F10_CUSTOS
```

Le preset est automatiquement mappé depuis le profil ATOM-IC via `CONFIG/atom_ic_profiles.json`.
