# Analyse des références « Smooth 120 FPS » et « 4K 120 FPS Cartoon »

## Conclusion essentielle

Ces deux vidéos ajoutent un élément que les premières références Topaz ne montraient pas assez clairement : le rendu que nous voulons dépasser n’est pas seulement une vidéo améliorée. C’est un **produit audiovisuel composé de trois fluidités différentes** : fluidité des images, fluidité du montage et fluidité des effets.

Une vidéo peut être techniquement à 120 FPS et rester molle si les cuts, les accélérations et les transitions sont mal construits. À l’inverse, une vidéo peut paraître extrêmement fluide grâce à une combinaison d’interpolation, de courbes de vitesse, de motion blur ou de netteté cristalline, de zooms et de synchronisation musicale.

## Métadonnées observées

| Référence | Résolution du fichier fourni | Cadence | Durée | Rôle de la référence |
|---|---:|---:|---:|---|
| How I Make Smooth 120FPS Viral Edits | 426×240 | 30 FPS | 163,56 s | Workflow humain, Flowframes/RIFE et finition After Effects |
| How to make 4K 120fps cartoon edits | 426×240 | 30 FPS | 482,46 s | Workflow mobile/cartoon, TimeCut, Alight Motion et Wink |

Les deux fichiers sont des copies YouTube en basse résolution, donc l’analyse des microtextures est limitée. En revanche, leur structure de workflow, leurs réglages visibles et leur logique de montage restent exploitables.

## Première référence : Smooth 120FPS Viral Edits

Le workflow observé sépare clairement la restauration et le mouvement. La source cinéma est annoncée autour de 23,976 FPS. Flowframes utilise RIFE 4.6 ou RIFE 4.25 pour produire une cadence élevée, souvent 120 FPS. Le fichier intermédiaire est conservé dans un format de haute qualité de type QuickTime/ProRes avant la finition.

La vidéo montre ensuite une composition After Effects à 60 FPS, avec **Frame Blending / Pixel Motion** et **Motion Blur** sur le calque interpolé. Cette étape est importante : les images supplémentaires produites à 120 FPS servent à rendre le mouvement plus organique lorsqu’il est ramené ou composé à une cadence de sortie plus basse.

La sensation de fluidité vient donc de plusieurs facteurs combinés : interpolation RIFE, densité temporelle supérieure, motion blur contrôlé, frame blending, zooms progressifs, speed ramps et cuts calés sur les impacts sonores. Les artefacts de warping sur les mains, lunettes ou mouvements complexes sont partiellement masqués par le motion blur et le montage rapide.

## Deuxième référence : 4K 120fps Cartoon Edits

Cette référence confirme que la fluidité ne dépend pas uniquement de Topaz. Le workflow utilise TimeCut avec Optical Flow en qualité élevée pour transformer les clips en 120 FPS. Alight Motion sert à l’édition, aux courbes de vitesse, au compositing et aux effets. Wink sert à l’amélioration Ultra HD, c’est-à-dire à un mélange de sharpening intelligent et d’amélioration de détail. L’export montré reste cependant en 1080p, malgré le titre 4K.

La vidéo insiste sur les courbes de vitesse : plusieurs points rapprochés produisent des accélérations et ralentis organiques. Les beats musicaux sont marqués avant le placement des clips. Des zooms, shakes légers, flashes, glow et calques Copy Background donnent de la cohérence au montage et masquent certaines transitions.

Cette référence montre aussi un style différent du rendu cinéma classique : la netteté reste volontairement très cristalline et le motion blur est limité. Dans ce contexte, la “fluidité virale” vient de l’interpolation et du speed ramping, mais aussi de la précision des cuts et de la netteté de chaque image.

## Ce qui explique le rendu spectaculaire

| Couche | Fonction | Effet perceptuel |
|---|---|---|
| Reconstruction/Enhance | Nettoyer la compression et reconstruire le détail | Visages, cheveux et textures plus riches |
| Upscale éventuel | Agrandir et densifier la sortie | Impression de définition supérieure, sans garantie de vrai détail |
| Interpolation | Créer des images intermédiaires | Mouvement plus continu |
| Motion blur/frame blending | Masquer les micro-erreurs et relier les images | Mouvement plus organique |
| Speed ramps | Accélérer et ralentir avec des courbes | Sensation de contrôle et de fluidité virale |
| Cuts sur les beats | Synchroniser image et son | Énergie et impact |
| Zooms/shakes/transitions | Ajouter une dynamique de caméra | L’image paraît plus vivante |
| Colorimétrie/compositing | Unifier les plans et créer le look | Contraste, profondeur et signature premium |

## Écart avec notre flotte actuelle

Notre flotte stable possède déjà une partie importante de la couche technique : RIFE 4.25, restauration faciale, texture, finition couleur et conservation de la cadence 120 FPS. Elle ne possède toutefois pas encore une véritable couche d’édition virale.

Nous traitons aujourd’hui principalement la vidéo comme un flux à améliorer image après image. Les nouvelles références traitent la vidéo comme une **timeline audiovisuelle** : les beats, les accélérations, les ralentis, les transitions, les zooms, les flashes et le mouvement de caméra participent autant au résultat que la restauration des pixels.

Notre F08 est encore une garde temporelle transparente. Nous n’avons pas encore de motion blur contrôlé, de frame blending sélectif, de courbes de vitesse ni de couche de montage pilotée par les beats. C’est une raison importante pour laquelle notre sortie peut être nette et fluide techniquement, tout en paraissant moins “virale” et moins spectaculaire.

## Cible recommandée pour v2

La branche v2 doit donc comporter deux axes séparés.

Le premier axe est **ATOM-IC ENHANCE**, destiné à la reconstruction spatiale : correction de compression, récupération de détails, débruitage modéré, anti-alias/deblur, dehalo adaptatif, restauration faciale et textures générales. C’est l’axe inspiré de Proteus.

Le deuxième axe est **ATOM-IC MOTUS VIRAL**, destiné à la perception du mouvement : interpolation à 120 FPS, contrôle des warps, frame blending optionnel, motion blur réglable, speed ramps, synchronisation des beats, zooms, shakes et transitions lumineuses. C’est l’axe révélé par les deux nouvelles références.

La cible ne doit pas appliquer tous les effets automatiquement à toutes les vidéos. Elle doit analyser le contenu et choisir un mode : cinéma naturel, viral agressif, anime/cartoon ou montage sombre. Les mouvements rapides devront recevoir une protection contre les artefacts, alors que les plans lents pourront recevoir une reconstruction de détail plus ambitieuse.

## Ordre idéal pour v2

L’ordre le plus cohérent devient : source → analyse F01 → nettoyage et reconstruction Enhance → restauration locale des visages et textures → colorimétrie → interpolation RIFE vers une cadence de travail élevée → motion blur/frame blending sélectif → montage, speed ramps et transitions → export final.

Pour une vidéo source déjà montée, le montage et les speed ramps peuvent rester facultatifs. Pour un objectif de type édits viraux, ils deviennent une partie de la qualité finale et non un simple accessoire.

## Verdict

Ces vidéos confirment que notre cible était trop étroite. Nous cherchions surtout à battre une qualité d’image. Le créateur que nous voulons dépasser produit probablement un résultat où **qualité d’image, fluidité temporelle et mise en scène du mouvement** sont combinées.

Le prochain saut de v2 ne doit donc pas être seulement un modèle plus agressif. Il doit être une architecture à deux moteurs : **Enhance pour la densité du détail et Motus Viral pour la perception du mouvement**. RIFE reste utile, mais il ne suffit pas à lui seul à produire le style “smooth viral”.
