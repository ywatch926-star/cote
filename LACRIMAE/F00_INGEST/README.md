# F00 INGEST — dev4

F00 prépare la matière première du Fast Match Cut en deux sous-étapes déterministes. **F00-A SCOUT** identifie et classe les passages exploitables. **F00-B EXTRACT** matérialise ensuite les séquences retenues avec FFmpeg et vérifie qu’elles sont lisibles avant F03 Preview et PICTOR.

## Entrées

Placez la vidéo dans `IN/video_source.mp4` et renseignez `IN/production_request.json` :

```json
{
  "project_title": "Luxury Match Cut 01",
  "target_duration_seconds": 10,
  "cut_interval_frames": 7,
  "candidate_count": 172,
  "scout_sample_fps": 2,
  "min_mean_luma": 0.075,
  "min_luma_std": 0.025,
  "min_candidate_gap_seconds": 0.35
}
```

## Exécution

```bash
python3 CODEBASE/f00_scout.py \
  --source IN/video_source.mp4 \
  --request IN/production_request.json \
  --out OUT/scout

python3 CODEBASE/f00_extract.py \
  --source IN/video_source.mp4 \
  --plan OUT/scout/sequences_plan.json \
  --out OUT/materialized
cp OUT/materialized/sequences.json OUT/sequences.json
```

## Sorties

`OUT/scout/sequences_plan.json` est le contrat Oracle de F00-A. Il contient les candidats, leurs scores de visibilité et les positions de timeline.

`OUT/materialized/sequences.json` est le contrat validé de F00-B. Il référence les fichiers `OUT/materialized/sequences/seq_XXXX.mp4`. Chaque séquence est un petit fichier H.264 indépendant, contrôlé avec FFprobe et une mesure de luminosité sur l’ensemble des frames.

Le schéma matérialisé est `dev4.materialized-sequences.v1`. Pour une cible de 10 secondes à environ 60 FPS et 7 frames par cut, il contient environ 86 séquences. F03 et PICTOR utilisent ces fichiers locaux ; ils ne doivent plus chercher aléatoirement les frames dans la source longue lorsqu’un champ `file` est présent.

`f00_ingest.py` reste disponible pour la compatibilité avec les anciens manifestes virtuels `dev4.virtual-sequences.v1`, mais le flux direct dev4 utilise désormais F00-A puis F00-B.

## F00-C Motion Slow (optionnelle)

F00-C ne s’exécute que lorsqu’elle est demandée par l’opérateur. Elle ne modifie jamais les sorties normales de F00-B et écrit ses résultats dans un dossier parallèle.

```bash
# Mode normal : copie validée, aucun traitement d’interpolation
python3 CODEBASE/f00_motion_slow.py \\
  --source IN/video_source.mp4 \\
  --manifest OUT/materialized/sequences.json \\
  --out OUT/motion_slow \\
  --mode off

# Mode partiel : effet uniquement entre 3 et 7 secondes
python3 CODEBASE/f00_motion_slow.py \\
  --source IN/video_source.mp4 \\
  --manifest OUT/materialized/sequences.json \\
  --out OUT/motion_slow \\
  --mode partial \\
  --speed 0.5 \\
  --ranges 3-7

# Mode global : effet sur toutes les séquences
python3 CODEBASE/f00_motion_slow.py \\
  --source IN/video_source.mp4 \\
  --manifest OUT/materialized/sequences.json \\
  --out OUT/motion_slow \\
  --mode global \\
  --speed 0.5
```

Le moteur initial est FFmpeg `minterpolate`. Les vitesses supportées sont 0,75×, 0,5× et 0,25×. Le manifeste `OUT/motion_slow/motion_slow_manifest.json` conserve les séquences normales hors des plages demandées et référence les séquences interpolées dans les plages actives. La durée timeline est conservée à la durée cible du manifeste F00-B.

Le workflow isolé `.github/workflows/dev4_f00c.yml` récupère un artifact F00-B validé et accepte les paramètres `off`, `partial` ou `global`. Il s’arrête après l’artifact F00-C : F03, PICTOR, F05 et F06 ne sont pas lancées automatiquement.

RIFE ncnn Vulkan est réservé à une future comparaison qualité. Il n’est pas proposé comme moteur exécutable dans le premier workflow tant que son modèle et son runner ne sont pas validés.
