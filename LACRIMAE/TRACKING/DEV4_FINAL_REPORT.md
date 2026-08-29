# Rapport final — LACRIMAE `dev4`

Date : 2026-08-22

## Résultat global

Le pipeline vidéo dev4 est maintenant structuré autour d’une source vidéo unique et de séquences virtuelles. F00 ne produit pas de clips intermédiaires : il écrit un manifeste JSON qui indique quelles frames de la source doivent apparaître sur la timeline finale. F03_PREVIEW lit ce manifeste pour montrer le Fast Match Cut et permet de valider les réglages. F03_PICTOR reprend la même composition Remotion pour rendre le MP4 final.

## Phases terminées

### F00 et contrat virtuel

`F00_INGEST/CODEBASE/f00_ingest.py` utilise FFprobe pour lire les caractéristiques de la source, calcule la durée cible, le nombre de frames et le nombre de séquences nécessaires, puis écrit `sequences.json` et `ingest_report.json`. Les séquences contiennent leur frame de départ dans la source et leur position dans la timeline finale. Aucun MP4 n’est écrit dans F00 OUT.

Un validateur commun, `tools/validate_dev4_contracts.py`, vérifie le schéma, la timeline, les durées, la monotonie des séquences et la présence de la source dans le codex.

### F03_PREVIEW

La preview existante a été conservée et raccordée au manifeste. Elle affiche le nombre de séquences, le rythme de coupe, les frames sources et la timeline. Le lecteur Remotion affiche les portions référencées de la vidéo originale sans créer de fichiers intermédiaires.

Les réglages existants restent disponibles : presets couleur, contraste, luminosité, grain, vignette, netteté, zoom, logo, texte et effets. La source vidéo est muette par défaut. L’export du codex inclut maintenant le manifeste virtuel et l’état de validation `validated_by_magos`.

### F03_PICTOR

PICTOR a été sorti de son ancien chemin Colab/images. Il possède désormais un package autonome dev4, un Root Remotion qui charge `codex.json` et `sequences.json`, et une copie de la composition commune utilisée par la preview. Le rendu headless produit `out/short_final.mp4`.

La parité de la composition et du résolveur de séquences entre preview et PICTOR a été vérifiée avec `cmp`. Le workflow resynchronise également ces deux fichiers avant le rendu afin d’éviter une divergence future.

### F05/F06 et skips des frégates

F05_CAMOUFLAGE reçoit `short_final.mp4`, réencode en H.264 `yuv420p` avec `+faststart`, supprime les métadonnées et gère correctement les vidéos sans audio. F06_LUTHER reçoit la sortie F05, retire les métadonnées résiduelles en stream copy, normalise le timestamp et produit `short_master.mp4` avec son rapport JSON.

Le workflow accepte `skip_f01`, `skip_f02`, `skip_f04`, `skip_f05` et `skip_f06`. F04 doit rester ignorée dans dev4 : PICTOR produit déjà le rendu. F05 et F06 sont actives par défaut ; leurs skips sont réservés au debug. Lorsque F01, F02 et F04 sont ignorées, le chemin normal est F00 → F03_PREVIEW → F03_PICTOR → F05 → F06. Les décisions sont inscrites dans `TRACKING/dev4_pipeline_state.txt`.

### GitHub Actions

Un job unique installe FFmpeg, Node.js et les dépendances Remotion, exécute F00, valide le manifeste, prépare les entrées communes, construit la preview, rend PICTOR, exécute F05 puis F06 et publie les JSON, les rapports, le build de preview et `short_master.mp4` comme artifact.

La vidéo source n’est pas commitée. Le runner attend `F00_INGEST/IN/video_source.mp4`. Le support d’une Release GitHub ou d’un stockage externe reste une amélioration ultérieure.

## Vérifications finales

| Vérification | Résultat |
|---|---|
| Test unitaire F00 | Réussi |
| F00 sur vidéo de test | Réussi |
| 10 secondes à 30 fps et 7 frames | 43 séquences virtuelles |
| Aucun clip dans F00 OUT | Confirmé |
| Validation des contrats JSON | Réussie |
| Build Vite de F03_PREVIEW | Réussi |
| Rendu PICTOR Remotion | Réussi, MP4 de 10,048 secondes |
| Parité preview / PICTOR | Confirmée |
| F05 sur vidéo muette | Réussi |
| F06 en stream copy | Réussi |
| Métadonnées finales suspectes | Aucune |
| Contrôle `git diff --check` | Réussi |

## Limites connues

La sélection F00 actuelle est déterministe et utilise un échantillonnage de positions dans la vidéo. Elle ne réalise pas encore une détection sémantique des plans par vision artificielle. Le pipeline produit donc un socle fonctionnel et reproductible, mais la qualité éditoriale des passages sélectionnés devra être améliorée dans une phase dédiée.

La validation humaine entre la preview et le rendu est représentée par l’export du codex validé. Le workflow actuel enchaîne ensuite le rendu dans le même job ; une vraie pause avec approbation GitHub devra être ajoutée si le Champion doit bloquer le rendu jusqu’à une validation manuelle formelle.

## Commit final

Commit fonctionnel : `263d0c848d7b85571ac46fc4467012e4e258cc2b` (`feat(dev4): complete virtual match-cut pipeline`). Le commit de skip F04 est `8909d27`. Le commit d’intégration F05/F06 est `60f000ec1d273d8ce43da332c6edf2426425aff7` (`feat(dev4): add camouflage and luther stages`). La branche `dev4` a été poussée sur `origin/dev4` et la branche `main` n’a pas été modifiée.

### Composition configurable et transformations

F03_PREVIEW et F03_PICTOR partagent désormais `compositionConfig.js`. Le codex définit le format final (`vertical`, `horizontal` ou `square`), le mode de recadrage (`cover` ou `contain`), le fond de remplissage (`blurred_video`, `solid` ou `none`), ainsi que la rotation (`none`, `per_sequence` ou `continuous`). La rotation peut viser le calque vidéo ou la composition entière.

La source horizontale réelle de la release `f00` a été rendue dans une composition verticale 1080×1920 avec un fond vidéo flouté et une rotation par séquence. Le rendu PICTOR et la preview ont réussi après normalisation de la source en H.264 yuv420p sans audio intermédiaire.

## Vérifications supplémentaires du 22 août 2026

| Vérification | Résultat |
|---|---|
| Build F03_PREVIEW avec les nouveaux contrôles | Réussi |
| Validation des compositions PICTOR | Réussie |
| Source f00 horizontale 1920×1080 vers canvas vertical | Réussi |
| Rotation par séquence | Rendue avec succès |
| Preview réelle de 10 secondes | MP4 vertical 1080×1920 produit |
| PICTOR réel de 10 secondes | MP4 vertical 1080×1920 produit |
| Découpage en fichiers intermédiaires | Aucun |
