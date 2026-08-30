# F03_AI — Neural Video Restoration Pipeline v3.1

## Architecture

```
VIDÉO BRUTE (30fps)
    │
    ▼
┌──────────────────────────────────────────┐
│  ÉTAPE 1: DIFFBIR (ECCV)                │  GPU: A10G
│  Upscale 720p → 1080p + textures        │
│  xpixelgroup/diffbir                    │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  ÉTAPE 2: L-DIFFUSER VCG (ICCV 2025)   │  GPU: A10G
│  Color grading via LUT 3D               │
│  seunghyuns98/VideoColorGrading         │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  ÉTAPE 3: AMT-G (CVPR 2023) + OpenCV   │  GPU: A10G
│  Interpolation 30→120fps + crunchy style │
│  mcg-nku/amt                            │
└──────────────────────────────────────────┘
    │
    ▼
VIDÉO FINALE 🎬 1080p | 120fps | Crunchy | Color Graded
```

## Scientific Sources

| Step | Model | Conference | Repository |
|------|-------|------------|------------|
| 1 | DiffBIR | ECCV | [XPixelGroup/DiffBIR](https://github.com/XPixelGroup/DiffBIR) |
| 2 | L-Diffuser VCG | ICCV 2025 | [seunghyuns98/VideoColorGrading](https://github.com/seunghyuns98/VideoColorGrading) |
| 3 | AMT-G | CVPR 2023 | [MCG-NKU/AMT](https://github.com/MCG-NKU/AMT) |

## Style Presets

| Preset | Sharpen | Saturation | Glow | Use Case |
|--------|---------|------------|------|----------|
| `default` | 1.2 | 1.1 | 0.4 | Balanced starting point |
| `demon` | 1.8 | 1.4 | 0.6 | Ultra-hard TikTok viral |
| `cinema` | 0.8 | 1.05 | 0.3 | Soft cinematic |
| `crunchy` | 1.5 | 1.3 | 0.5 | Strong viral look |

## Usage

### CLI
```bash
python F03_AI/modal/orchestrator.py input.mp4 reference.png output.mp4 --style crunchy
```

### Modal Deploy
```bash
modal deploy F03_AI/modal/diffbir_pipeline.py
modal deploy F03_AI/modal/vcg_pipeline.py
modal deploy F03_AI/modal/amt_pipeline.py
```

### GitHub Actions
Push to `dev6-D` or trigger manually from Actions tab.

## Cost Estimate

| Step | GPU | Time (5s video) | Cost |
|------|-----|-----------------|------|
| DiffBIR | A10G | ~30s | ~$0.009 |
| VCG | A10G | ~15s | ~$0.005 |
| AMT-G + Style | A10G | ~60s | ~$0.018 |
| **Total** | | **~105s** | **~$0.032** |

## Configuration

- `config.py` — GPU, timeouts, model paths
- `PRESETS/style_presets.json` — OpenCV crunch presets
- `PRESETS/color_ref_presets.json` — Color reference mappings
