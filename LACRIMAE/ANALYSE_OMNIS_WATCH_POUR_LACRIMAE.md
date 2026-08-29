# Analyse d’OMNIS_WATCH pour LACRIMAE

## Source examinée

Dépôt : `https://github.com/kioka8877-ux/OMNIS_WATCH`
Branche examinée : `dev2`
Zone demandée : `TRACKING/` et documents associés.

## Organisation observée

OMNIS_WATCH structure chaque génération autour de Frégates spécialisées et de dossiers `IN/`, `OUT/`, `CODEBASE/` et `TRACKING.md`. Le dépôt conserve une documentation de campagne, un journal de transfert, un `TODO_CONTINUATION.md`, un `HANDOVER`, des documents `OMNIS_COLD_START.md`, des contrats de métaprompt et un ledger JSON.

L’architecture sépare clairement :

- le sandbox et l’Oracle, utilisés pour la décision, le métaprompt et la préparation ;
- GitHub Actions, utilisé comme usine reproductible pour FFmpeg, MediaPipe, Remotion et le mixage ;
- le PC opérateur, utilisé pour la réception et les gates de validation.

Le point fort n’est pas seulement la nomenclature. C’est la traçabilité : chaque Frégate possède un périmètre, des entrées, des sorties, un runner et un document de suivi. Le ledger conserve l’état de la campagne et le handover permet à un autre sandbox de reprendre sans deviner.

## Différences avec LACRIMAE v2

LACRIMAE v2 possède déjà une meilleure chaîne GPU spécialisée pour la vidéo : RIFE 4.25, GFPGAN, F00-F10, AUSPEX, profils ATOM-IC et Modal. En revanche, OMNIS_WATCH est plus mature sur la documentation opératoire, les gates, les handovers, l’isolation des entrées/sorties et la séparation des responsabilités.

LACRIMAE doit donc reprendre la discipline documentaire d’OMNIS sans copier ses fonctions de contenu :

1. un fichier de continuité central obligatoire ;
2. un ledger de campagne et de validation ;
3. un contrat par Frégate avec entrée, sortie, runner, coût et métriques ;
4. un tracking par étape ;
5. des gates explicites avant GPU, après Enhance, après fluidité et avant livraison ;
6. un manifeste de reprise pour les modèles, Volumes et variables ;
7. une séparation claire entre branche stable, branche d’expérimentation et branche spécialisée.

## Décision sur dev7

La création d’une branche `dev7` est pertinente pour isoler le périmètre **120 FPS**. Elle doit partir de `v2`, qui contient l’analyse adaptative et les profils Motus, afin de ne pas perdre les travaux déjà réalisés. `dev7` devient la branche d’intégration et de validation dédiée à la chaîne 120 FPS ; `v2` reste la branche de développement général ; `dev6` reste la base stable.

Il ne faut pas dupliquer aveuglément tout le dépôt dans une nouvelle arborescence lourde. Il vaut mieux conserver le code partagé dans les mêmes modules, puis ajouter dans `dev7` une documentation et une configuration explicitement marquées `120 FPS`, ainsi qu’un ledger de campagne dédié. Les modèles, vidéos et secrets restent hors GitHub.

## Libellé GitHub

Un label GitHub `120 fps` est pertinent pour les issues, pull requests et discussions liées à dev7. Un label GitHub n’est pas attaché techniquement à une branche ; il est attaché aux issues et pull requests du dépôt. Pour rendre la branche impossible à oublier, il faut combiner :

- le nom de branche `dev7` ;
- le libellé GitHub `120 fps` ;
- un fichier `DEV7_120FPS_SCOPE.md` ;
- un ledger et un tracking dédiés ;
- une description de branche et un README de reprise qui mentionnent `120 FPS`.

## Impact sur le plan

Le plan v2 est modifié sur l’organisation, pas sur l’objectif visuel. Avant de poursuivre les presets After Effects, il faut créer le socle dev7 120 FPS, y transférer les éléments de gouvernance et de validation, puis continuer le travail F09 AETHER COMPOSITUM dans ce périmètre.

L’ordre recommandé devient : gouvernance dev7 → analyse AUSPEX → Enhance → RIFE/120 FPS → Motus Viral → presets multicouches → validation comparative vidéo contre vidéo.

## Conclusion

OMNIS_WATCH ne remplace pas la technologie LACRIMAE ; il améliore sa discipline de production. LACRIMAE doit adopter son système de tracking, son handover, ses gates, ses ledgers et sa séparation Oracle/usine. `dev7` est donc justifié comme branche dédiée au parcours 120 FPS, avec un label GitHub `120 fps` et une documentation explicite.
