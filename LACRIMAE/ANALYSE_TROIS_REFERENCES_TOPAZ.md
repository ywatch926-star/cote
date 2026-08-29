# Analyse comparative des trois références Topaz

## Conclusion principale

Les trois vidéos indiquent que le saut qualitatif recherché ne vient pas d’abord de la 4K ni du 120 FPS. Le cœur du rendu est une étape d’**Enhance par reconstruction de détail**, réalisée avec Proteus en réglage manuel, puis une finition esthétique séparée dans After Effects. L’interpolation arrive ensuite, notamment avec RIFE via Flowframes, afin de ne pas interpoler une image encore pleine d’artefacts.

## Références analysées

| Référence | Résolution observée | Cadence observée | Durée | Indice principal |
|---|---:|---:|---:|---|
| High Quality / 4K tutorial | 640×360 | 25 FPS | 102,38 s | Proteus + upscale 2× vers 3840×2160 + Chronos vers 60 FPS + After Effects |
| Smooth 120 FPS tutorial | 1920×1080 | 60 FPS | 347,79 s | Proteus à échelle 100 %, After Effects, puis RIFE x2/x4 vers 120 FPS |
| Best Topaz settings | 640×360 | 23,976 FPS | 403,54 s | Proteus manuel pour reconstruire le détail, puis correction couleur dans After Effects |

Les fichiers analysés contiennent tous une piste audio AAC stéréo à 44,1 kHz. Les deux références 360p sont des extraits de tutoriels et ne constituent pas des preuves que toute la vidéo finale est réellement exportée en 4K ; elles montrent surtout l’interface et la méthode.

## Réglages observés dans les tutoriels

| Paramètre Proteus | Référence 1 | Référence 2 | Référence 3 | Interprétation |
|---|---:|---:|---:|---|
| Revert Compression | 80 | 95 | 90 | Nettoyage très fort avant reconstruction |
| Recover/Improve Details | 90 | 100 | 85 | Reconstruction agressive des détails |
| Sharpen | 50 | 40 | 75 | Netteté secondaire, pas le moteur principal |
| Reduce Noise | 40 | 10 | 55 | Réduction adaptée à la qualité de la source |
| Dehalo | 0 | 20 | 5 | Contrôle des liserés autour des contours |
| Anti-Alias / Deblur | 100 | 49 | 50 | Récupération du flou et des contours |

Ces valeurs ne doivent pas être copiées aveuglément. Elles montrent toutefois une hiérarchie claire : **Revert Compression et Recover Details sont prioritaires ; Sharpen reste modéré ou contrôlé**. Le rendu premium vient donc davantage d’une reconstruction apprise que d’un filtre de netteté.

## Ordre de traitement révélé

Le workflow le plus crédible observé est :

> Source compressée → Enhance/Proteus → export intermédiaire de haute qualité → correction couleur After Effects → interpolation RIFE → export final.

La première référence montre aussi un cas où Proteus est combiné à un upscale 2× et à Chronos vers 60 FPS. La deuxième montre plus clairement la séparation entre l’amélioration spatiale Proteus et l’interpolation RIFE vers 120 FPS. La troisième confirme qu’un rendu convaincant peut être obtenu à résolution originale, sans que l’upscale 4K soit le facteur essentiel.

## Ce que l’œil voit réellement

L’Enhance reconstruit ou densifie les éléments qui nous manquent encore : pores et dégradés de peau, reflets des yeux, mèches de cheveux, barbe, fibres de vêtements, logos et contours fins. Il réduit les blocs de compression avant d’ajouter du détail. Il ne se contente donc pas d’accentuer les contours déjà présents.

After Effects joue un rôle différent. Il apporte la signature esthétique : contraste en S, noirs plus profonds, hautes lumières plus fortes, saturation sélective, teinte cinématique et séparation plus nette entre sujet et arrière-plan. Cette étape explique une grande partie de l’impact immédiat observé dans les exemples.

L’interpolation RIFE apporte la fluidité. Elle n’est pas responsable de la richesse des textures. Elle doit idéalement être appliquée après la restauration spatiale, afin de ne pas propager les artefacts de compression et de netteté dans les images intermédiaires.

## Écart avec notre version actuelle

Notre version stable `dev6` possède déjà RIFE 4.25, GFPGAN v1.3, des filtres de restauration FFmpeg, F04 texture et F07 Chroma Dominatus. Elle atteint donc la bonne architecture générale, mais pas encore la même classe de reconstruction.

Le manque principal est un **Enhance généraliste appris**, équivalent fonctionnel de Proteus. GFPGAN travaille surtout sur les visages ; F03, F04, F06 et F07 utilisent principalement des filtres déterministes. Ces filtres peuvent nettoyer, accentuer et colorer, mais ils ne reconstruisent pas suffisamment les textures de cheveux, de peau, de tissu et de décor.

Notre autre différence est l’ordre effectif : nous avons beaucoup travaillé sur RIFE et la finition, alors que les références placent la reconstruction du signal avant la finition couleur et avant l’interpolation finale. Enfin, notre F08 de cohérence temporelle est encore transparent ; il n’existe pas encore de passe active qui stabilise les détails reconstruits sans produire de ghosting.

## Cible technique pour v2

La cible la plus pertinente n’est pas « produire systématiquement de la 4K ». Elle est :

1. Ajouter un moteur d’Enhance généraliste ou une combinaison de restauration plus puissante que GFPGAN seul.
2. Nettoyer la compression avec une intensité élevée, mais conserver un débruitage modéré pour protéger les textures organiques.
3. Reconstruire le détail avec une force élevée, tout en limitant le sharpening final.
4. Appliquer un dehalo et un antialias/deblur adaptatifs selon le type de scène.
5. Séparer strictement la reconstruction technique de la colorimétrie artistique.
6. Interpoler vers 120 FPS après la reconstruction spatiale, avec une vérification des warps.
7. Exporter les intermédiaires avec une compression suffisamment faible pour ne pas détruire le détail entre les étapes.

## Verdict

Ces vidéos confirment que notre intuition précédente était incomplète. Le niveau supérieur ne vient pas simplement de meilleurs paramètres GFPGAN ou d’un grade HDR plus agressif. Il vient d’une **vraie étape Enhance de reconstruction générale**, puis d’une colorimétrie bien dirigée. La 4K est une sortie possible, mais elle n’est pas la cause principale du rendu premium.

La branche `v2` doit donc être orientée vers cette priorité : trouver ou intégrer une brique de reconstruction générale compatible avec notre environnement Modal, puis recalibrer F03/F04/F05/F07 autour de cette brique. Les réglages Proteus observés servent de cible comportementale, pas de preuve que nous pouvons reproduire exactement le modèle sans disposer de ses poids et de son moteur.
