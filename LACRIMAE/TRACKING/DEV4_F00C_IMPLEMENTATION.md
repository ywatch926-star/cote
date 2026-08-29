# DEV4 — F00-C Motion Slow

## Objectif

F00-C est une étape optionnelle d’interpolation de mouvement. Elle ne modifie pas les sorties normales de F00-B et n’est exécutée que lorsque l’opérateur choisit un mode Motion Slow.

## Modes opérateur

- `off` : copie validée des séquences F00-B, sans interpolation.
- `partial` : interpolation uniquement des plages demandées en secondes, par exemple `3-7`.
- `global` : interpolation de toutes les séquences.

Les vitesses supportées dans la première version sont 0,75×, 0,5× et 0,25×. Le moteur validé est FFmpeg `minterpolate`. RIFE ncnn Vulkan est documenté comme futur moteur qualité, mais n’est pas encore activé dans le workflow.

## Sorties

F00-C publie `motion_slow_manifest.json`, `motion_slow_report.json` et un dossier `sequences/` parallèle aux sorties F00-B. Chaque ligne du manifeste indique si la séquence est normale ou interpolée, la vitesse et le moteur utilisés.

La durée de la timeline est conservée à la durée du manifeste F00-B par recoupe contrôlée des sorties interpolées.

## Tests locaux

Source utilisée : asset vidéo de la release `f00`.

- Les tests unitaires F00 ont réussi : 5 tests.
- Le mode `off` a produit 86 sorties, 0 séquence traitée et 599 frames, soit 9,993 secondes à 59,94 FPS.
- Le mode `partial`, plage `3-7`, vitesse `0,5×`, a traité 35 séquences sur 86 et a produit 599 frames, soit 9,993 secondes.
- La compilation Python a réussi.
- Le build Vite F03 a réussi avec 40 modules transformés.
- Le contrôle `git diff --check` a réussi.

## Intégration F03

F03 tente de charger `motion_slow_manifest.json` en priorité lorsqu’il est installé dans `public/`, puis revient automatiquement à `sequences.json`. Le panneau Vidéo permet de préparer le mode, la vitesse, les plages et le moteur, puis d’exporter ces paramètres dans le codex. Le navigateur ne lance pas F00-C directement.

## Workflow

`.github/workflows/dev4_f00c.yml` est un workflow manuel isolé. Il récupère un artifact F00-B validé, télécharge la source, exécute F00-C et publie uniquement l’artifact F00-C. Il ne lance ni F03, ni PICTOR, ni F05, ni F06.

Auteur : Manus AI
Date : 2026-08-24
