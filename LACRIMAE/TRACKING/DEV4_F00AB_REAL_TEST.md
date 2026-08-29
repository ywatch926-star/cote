# DEV4 — test réel F00-A / F00-B

## Architecture exécutée

Le test réel a utilisé la vidéo f00 `video_source.mp4` et le flux suivant :

```text
F00-A SCOUT → F00-B EXTRACT → F03 PREVIEW → PICTOR → F05 CAMOUFLAGE → F06 LUTHER
```

F00-A a échantillonné la source avec FFmpeg, classé les passages par luminosité et variance, puis produit `sequences_plan.json`. Le plan contient 61 candidats exploitables et 86 séquences nécessaires pour une cible de 10 secondes à environ 60 FPS, avec 7 frames par cut.

F00-B a matérialisé les 86 séquences en petits fichiers H.264 indépendants dans `F00_INGEST/OUT/real_f00b/sequences/`. Chaque fichier a été contrôlé avec FFprobe et une analyse de luminosité sur l’ensemble de ses frames. Le manifeste final est `dev4.materialized-sequences.v1`, avec `materialized: true` et `validated: true` pour chaque séquence.

## Vérifications

| Étape | Résultat |
|---|---|
| F00-A | Réussi : 61 candidats, 86 séquences planifiées |
| F00-B | Réussi : 86/86 séquences matérialisées et validées |
| Contrat JSON | Réussi : 86 séquences, 599 frames |
| F03 Preview | Réussi : le lecteur charge `sequences/seq_0009.mp4`, durée 0,116783 s, readyState 4 |
| PICTOR | Réussi : MP4 1080×1920, 599 frames, environ 9,99 s |
| F05 Camouflage | Réussi : QA pass |
| F06 Luther | Réussi : metadata résiduelle supprimée, QA pass |

## Décision technique

F03 et PICTOR ne cherchent plus les frames dans la vidéo source longue lorsqu’un champ `file` matérialisé est disponible. Ils lisent le fichier MP4 local de la séquence. Le retour à la vidéo source reste possible pour les anciens manifestes virtuels.

Le background reste masqué dans le preset actuel, les textes et flashs sont désactivés, et le logo reste conservé. Le gate Champion a été ajouté au workflow avant le rendu PICTOR ; il doit être explicitement approuvé après examen de F03.

## Sorties locales

- `F00_INGEST/OUT/real_f00a/sequences_plan.json`
- `F00_INGEST/OUT/real_f00b/sequences.json`
- `F03_PICTOR/CODEBASE/out/short_final.mp4`
- `F05_CAMOUFLAGE/OUT/short_camouflaged.mp4`
- `F06_LUTHER/OUT/short_master.mp4`
