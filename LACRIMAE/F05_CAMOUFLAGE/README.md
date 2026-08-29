# F05_CAMOUFLAGE — dev4

F05 reçoit le rendu `short_final.mp4` produit par F03_PICTOR et prépare une version destinée à la livraison. Il réencode la vidéo en H.264 `yuv420p`, applique `+faststart`, supprime les métadonnées de conteneur et produit un rapport QA JSON.

F05 gère deux cas : une vidéo sans audio reste sans audio ; une piste audio présente est réencodée en AAC et normalisée à -14 LUFS.

```bash
python3 F05_CAMOUFLAGE/CODEBASE/lac_f05_camouflage.py \
  --input F05_CAMOUFLAGE/IN/short_final.mp4 \
  --output F05_CAMOUFLAGE/OUT
```

Sorties :

```text
F05_CAMOUFLAGE/OUT/
├── short_camouflaged.mp4
└── camouflage_report.json
```

F05 ne modifie pas les séquences virtuelles et ne refait pas le montage. Il intervient uniquement après le rendu PICTOR.
