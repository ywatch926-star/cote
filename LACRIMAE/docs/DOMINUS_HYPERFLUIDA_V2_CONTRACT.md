# Contrat DOMINUS HYPERFLUIDA v2

# Contrat DOMINUS HYPERFLUIDA — LACRIMAE dev6-B (v2)

## Contrat général

La branche active est `dev6-B`; `dev6` reste stable. Chaque Frégate reçoit une vidéo et un identifiant de campagne. Elle écrit une sortie distincte, un rapport JSON et les métriques utiles. Elle ne doit jamais écraser son entrée. Les chemins doivent rester relatifs au Volume et ne peuvent pas remonter dans l’arborescence.

## Contrat F01 AUSPEX OCULUS

F01 est local et sans GPU. Il reçoit la source originale, extrait un nombre limité de frames, calcule les mesures pixel et temporelles, puis écrit une recommandation. Il ne modifie pas la vidéo.

Les champs minimaux sont `metadata`, `pixel`, `temporal` et `recommendation`. La recommandation contient un `profile` et un `motus_mode`. Le mode `auto` de l’Oracle utilise le profil recommandé avant l’appel GPU.

## Contrat ATOM-IC ENHANCE

F03 réduit les défauts de compression et le bruit. F04 travaille sur la texture et les contours. F05 travaille exclusivement sur les visages détectés et doit utiliser un poids facial issu du profil. Ces étapes conservent la résolution native par défaut.

## Contrat ATOM-IC MOTUS VIRAL

F02 produit la cadence cible avec RIFE. F08 contrôle la stabilité temporelle. Une stabilisation active doit être explicitement configurée ; par défaut, la garde est transparente afin d’éviter de créer du ghosting sans validation.

Le mode viral peut ajouter frame blending et motion blur contrôlés par `motus.frame_blend` et `motus.motion_blur`. Les speed ramps, zooms, shakes et transitions restent des fonctions de montage séparées, afin de ne pas confondre reconstruction de détail et mise en scène. Le profil `viral_imperator` active uniquement de faibles valeurs expérimentales tant qu’un test vidéo n’a pas confirmé l’absence de ghosting.

## Contrat CHROMA DOMINATUS

F06 et F07 appliquent lumière, contraste, saturation et teinte après la restauration. Les profils doivent protéger les tons chair, les hautes lumières et les zones sombres. Aucun profil ne doit supposer que la source est horizontale, verticale ou carrée.

## Contrat de suivi

Chaque campagne doit être enregistrée dans `TRACKING/dev6b_campaign_ledger.json` et suivre les gates G0 à G9 définis dans `TRACKING/DEV6B_GATES.md`. Une tentative échouée reçoit un nouvel identifiant et ne doit pas écraser les rapports précédents.

## Contrat de sortie

F10 vérifie la présence du fichier final, sa résolution, sa cadence, sa durée, son hash et les pistes audio. Une sortie est considérée comme scellée seulement si les rapports de toutes les étapes sont disponibles et cohérents avec la campagne.
