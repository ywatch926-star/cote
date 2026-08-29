# LACRIMAE — REGISTRE DES TRANSFERTS
> *"Aucun transit n'existe sans inscription dans ce registre."*
> Matrice de traçabilité des flux — Rempli par le Magos lors des transferts manuels

---

## MODE D'EMPLOI

1. Avant chaque transfert : lancer `python LAC_CUSTOS.py --frigate [SOURCE] --mode check-out`
2. Copier manuellement les fichiers vers la frégate destinataire sur Drive
3. Après chaque transfert : lancer `python LAC_CUSTOS.py --frigate [DEST] --mode check-in`
4. Inscrire le résultat dans le registre ci-dessous

---

## REGISTRE DES TRANSFERTS

| # | Date | Croisade | Source | Destination | Fichiers | Custos Out | Custos In | Statut |
|---|------|----------|--------|-------------|----------|------------|-----------|--------|
| 1 | 2026-05-19 | FORGE ALPHA | F01 OUT | F02 IN | `timing.json` | ✅ | ✅ | 🟢 SCELLÉ |
| 2 | 2026-05-19 | FORGE ALPHA | SHARED | F02 IN | `images/*.jpg/png` | — | ✅ | 🟢 SCELLÉ |
| 3 | 2026-05-19 | FORGE ALPHA | F01 OUT | F03 IN | `timing.json` | ✅ | ✅ | 🟢 SCELLÉ |
| 4 | 2026-05-19 | FORGE ALPHA | F02 OUT | F03 IN | `creative_config.json` | ✅ | ✅ | 🟢 SCELLÉ |
| 5 | 2026-05-19 | FORGE ALPHA | SHARED | F03 IN | `audio_clean.mp3`, `images/` | — | ✅ | 🟢 SCELLÉ |
| 6 | 2026-05-19 | FORGE ALPHA | F03 OUT | F04 IN | `short_final.mp4` (65.3 Mo) | ✅ | — | 🔵 En transit |
| 7 | 2026-05-19 | FORGE ALPHA | F01 OUT | F04 IN | `timing.json` | ✅ | — | 🔵 En transit |

---

## MATRICE DES FLUX STANDARD

| De → Vers | Fichiers transférés | Format |
|-----------|---------------------|--------|
| SHARED → F01 | `audio_clean.mp3` | .mp3 |
| SHARED → F02 | `images/*.jpg/png` | .jpg .png |
| SHARED → F03 | `audio_clean.mp3`, `images/*.jpg/png` | .mp3, .jpg .png |
| F01 → F02 | `timing.json` | .json |
| F01 → F03 | `timing.json` | .json |
| F01 → F04 | `timing.json` | .json |
| F02 → F03 | `creative_config.json` | .json |
| F03 → F04 | `short_final.mp4` | .mp4 |
| F04 → Magos | `short_master.mp4` | .mp4 |

**Légende** : ⬜ Non vérifié | ✅ Validé | ❌ Échoué

---

## ROUTING COMPLET

```
SHARED/audio_clean.mp3 ─────────────────────────────► F01, F03
SHARED/images/ ─────────────────────────────────────► F02, F03

F01 CANTOR ──► timing.json ─────────────────────────► F02, F03, F04

F02 VISIO ──► creative_config.json ─────────────────► F03

F03 PICTOR ──► short_final.mp4 ─────────────────────► F04

F04 SIGNUM ──► short_master.mp4 ────────────────────► MAGOS (téléchargement)
```

---

## FORMAT timing.json (OUT de F01)

```json
{
  "audio_duration_s": 8.5914,
  "total_frames": 258,
  "fps": 30,
  "words": [
    {
      "word": "night",
      "start_s": 7.45,
      "end_s": 7.63,
      "start_frame": 223,
      "end_frame": 229,
      "is_strong": true
    }
  ]
}
```

---

## FORMAT creative_config.json (OUT de F02)

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

---

## RÉFÉRENCES

- [Carnet de Campagne](./LACRIMAE_CAMPAIGN_LOG.md) — État des frégates
- [LAC_CUSTOS](../LAC_CUSTOS.py) — Script de validation logistique
- [README](../README.md) — Documentation principale
