# F02 VISIO — README DÉVELOPPEUR
> *"Le Visionnaire contemple. La forme prend sens avant le rendu."*

---

## Mission

Servir un viewer HTML interactif via Flask + port Colab natif. Permet de prévisualiser le timing mot par mot, les images en fast cut, les filtres CSS et les sous-titres. Produit `creative_config.json` validé par le Magos.

---

## Technologie

| Composant | Version cible |
|-----------|---------------|
| Python | 3.10+ |
| Flask | ≥ 3.0.0 |
| Port Colab | `google.colab.output.eval_js` (natif, pas de ngrok) |

---

## Fichiers

| Fichier | Rôle |
|---------|------|
| `LAC_F02.ipynb` | Notebook Colab — point d'entrée opérateur |
| `lac_f02_flask.py` | Serveur Flask (API REST + routing) |
| `lac_f02_viewer.html` | Interface HTML (timeline, preview phone, sliders) |
| `README_DEV.md` | Ce fichier |

---

## API Endpoints

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Viewer HTML |
| `/api/timing` | GET | timing.json complet |
| `/api/images` | GET | Liste des images disponibles |
| `/api/image/<filename>` | GET | Sert une image |
| `/api/config` | GET | creative_config.json actuel |
| `/api/config` | POST | Sauvegarde la config validée |
| `/api/status` | GET | État de la frégate |

---

## Inputs / Outputs

```
IN/
├── timing.json         ← De F01 CANTOR (transit manuel)
└── images/             ← De SHARED/ (transit manuel)
    ├── img_01.jpg
    └── ...

OUT/
└── creative_config.json
```

---

## Format creative_config.json

```json
{
  "fps": 30,
  "resolution": { "width": 1080, "height": 1920 },
  "cut_interval_frames": 7,
  "image_order": "sequential",
  "font_main": "Cinzel",
  "font_strong": "Playfair Display",
  "text_color": "#FFFFFF",
  "text_shadow": "0px 4px 12px rgba(0,0,0,0.9)",
  "letter_spacing": "0.12em",
  "grain_overlay_opacity": 0.30,
  "css_filters": "contrast(1.2) brightness(0.88) sepia(0.15)",
  "blend_mode": "screen",
  "word_animation": "fade",
  "validated_by_magos": true
}
```

**Important** : `validated_by_magos` est positionné à `true` automatiquement lors du clic sur "SCELLER LA CONFIG" dans le viewer.

---

## Rites du Sang applicables

- **LOI D'ISOLEMENT** : VISIO ne lit que `F02/IN/`. Aucun accès aux autres frégates.
- **RITE DE VALIDATION** : LAC_CUSTOS check-in avant démarrage, check-out avant transit.
- **TRANSIT MANUEL** : Le Magos copie les images et timing.json. Jamais automatisé.
