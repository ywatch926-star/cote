# F06_LUTHER — dev4

F06 reçoit `short_camouflaged.mp4` et produit le livrable final `short_master.mp4`. Il retire les métadonnées restantes avec FFmpeg en stream copy, sans réencoder la vidéo, normalise le timestamp du fichier et vérifie l’absence de tags suspects.

```bash
python3 F06_LUTHER/CODEBASE/lac_f06_luther.py \
  --input F06_LUTHER/IN/short_camouflaged.mp4 \
  --output F06_LUTHER/OUT
```

Sorties :

```text
F06_LUTHER/OUT/
├── short_master.mp4
└── luther_report.json
```

F06 ne modifie ni le Fast Match Cut, ni la colorimétrie, ni les séquences. Il intervient après F05 comme opération finale de nettoyage et de contrôle.
