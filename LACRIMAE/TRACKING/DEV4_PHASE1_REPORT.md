# Rapport de phase 1 — LACRIMAE `dev4`

Date : 2026-08-22

## Objectif

Mettre en place le socle du nouveau flux vidéo `dev4` : F00 produit un manifeste de séquences virtuelles, F03_PREVIEW visualise ces séquences, F03_PICTOR rend la même composition Remotion et le workflow permet de sauter explicitement F01 et F02.

## Réalisations

F00 a été créé dans `F00_INGEST/CODEBASE/f00_ingest.py`. Il interroge les métadonnées de la vidéo avec FFprobe, calcule la durée cible et le nombre de frames de la timeline, puis écrit `OUT/sequences.json`. Aucun clip intermédiaire ni aucune copie vidéo n’est produite dans `OUT`.

F03_PREVIEW a été raccordé à `sequences.json`. L’application conserve son interface React/Remotion et ses contrôles visuels, mais la composition peut maintenant afficher les portions référencées par leur frame de départ dans la vidéo source. La vidéo source est muette par défaut. Le manifeste est également passé au Root Remotion utilisé pour le rendu de test.

F03_PICTOR a reçu une composition dev4 basée sur la même `OmniComposition` que la preview, ainsi qu’un contrat autonome `codex.json` + `sequences.json`. L’ancien Root Colab a été conservé sous `Root.colab.legacy.jsx` comme référence historique, mais il n’est plus le chemin actif du rendu dev4.

Le workflow `.github/workflows/dev4_pipeline.yml` exécute un job linéaire F00 → Preview → PICTOR. Ses entrées `skip_f01` et `skip_f02` sont explicites. En mode direct, les deux frégates sont journalisées comme ignorées ; si une frégate est demandée, le workflow vérifie la présence de sa sortie attendue.

## Vérifications effectuées

| Vérification | Résultat |
|---|---|
| Génération F00 sur vidéo de test | Réussie |
| Manifest virtuel sans extraction de clips | Réussie |
| Calcul 1 seconde à 30 fps et 7 frames | 5 séquences produites |
| Build Vite de F03_PREVIEW | Réussi |
| Rendu Remotion de F03_PICTOR sur vidéo de test | Réussi |
| Nettoyage des dépendances et sorties locales | Effectué |
| Modification de la branche `main` | Aucune |

## Limites connues pour la phase suivante

La sélection actuelle de F00 est déterministe et basée sur un échantillonnage de repères temporels ; elle ne réalise pas encore une analyse sémantique des plans. Le Champion peut valider le manifeste, mais l’interface de remplacement séquence par séquence devra être approfondie. Le workflow construit la preview et le rendu dans le même job, mais une étape de validation humaine formelle entre les deux devra être ajoutée si le processus exige un arrêt avant PICTOR.

La vidéo source reste volontairement hors du dépôt et doit être fournie au runner via `F00_INGEST/IN/video_source.mp4` ou un mécanisme d’asset externe à ajouter ultérieurement. F00 OUT ne contient que les JSON de contrôle.
