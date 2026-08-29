# Plan d’implémentation — ATOM-IC NORAGE Finish

## Objectif

Faire évoluer la flotte DOMINUS HYPERFLUIDA d’un rendu principalement fondé sur l’interpolation, la restauration et la netteté vers une finition visuelle plus cinématographique. L’objectif est de récupérer les leviers visibles dans les aperçus publics de NORAGE — contraste, HDR, séparation du sujet, tonalité réaliste et cohérence de look — tout en conservant notre traitement adaptatif et notre exécution serverless.

La cible prioritaire reste la **qualité perçue**, et non le simple nombre de pixels. Le test de référence sera exécuté à partir de `/home/ubuntu/upload/rife_input_5s.mp4`, sans réutiliser une sortie déjà traitée comme entrée.

## Principe d’architecture

Le pipeline conserve RIFE 4.25 pour la conversion 30 → 120 FPS et GFPGAN v1.3 pour la restauration faciale ciblée. Une nouvelle sous-frégate F07 sera ajoutée après la restauration faciale et la texture, mais avant la restitution finale F10.

```text
F00 AUDITUS
  → F01 AUSPEX OCULUS
  → F02 MOTUS RIFE
  → F03 APOTHECA RESTAURA
  → F04 FORGE TEXTURA
  → F05 LIBRARIUS FACIES
  → F06 LUMEN IGNIS
  → F07 CHROMA DOMINATUS
  → F08 TEMPORALIS CONSISTENTIA
  → F10 CUSTOS RESTITUTIO
```

F07 ne doit pas remplacer les étapes de détail. Il doit produire la signature finale de l’image à partir d’une image déjà restaurée. F08 pourra être activée pour les vidéos où le contraste ou les textures scintillent après traitement.

## Phase 1 — Stabiliser la base et les critères de réussite

Avant toute modification lourde, conserver la sortie actuelle comme référence de contrôle. Le fichier source sera comparé au résultat actuel sur les mêmes instants et avec les mêmes métadonnées.

Les critères de réussite sont les suivants : le visage doit être plus lisible sans peau cireuse ; les cheveux doivent gagner en séparation sans halo noir ; le costume et les zones sombres doivent garder une texture perceptible ; les hautes lumières doivent rester contrôlées ; la colorimétrie doit donner un impact immédiat sans détruire les tons chair ; enfin, les textures doivent rester stables entre images.

Le 120 FPS et la résolution 1920×1080 seront vérifiés à chaque variante. Aucun upscale 4K ne sera ajouté à cette phase.

## Phase 2 — Créer F07 CHROMA DOMINATUS

Créer un module indépendant dans `modal/workers` ou dans le runtime partagé, avec une fonction de traitement déterministe et un profil JSON dans `CONFIG/atom_ic_profiles.json`. La sous-frégate devra fonctionner avec FFmpeg et/ou OpenCV, sans dépendre d’After Effects.

Trois profils seront implémentés :

| Profil | Usage | Traitement principal |
|---|---|---|
| `hdr_imperator` | Montages spectaculaires, explosions, lumières, scènes à fort impact | Courbe HDR douce, contraste local renforcé, hautes lumières comprimées, saturation sélective contrôlée |
| `realistic_aurea` | Visages, interviews, scènes naturelles et vidéos humaines | Contraste plus doux, tons chair protégés, saturation modérée, détail naturel |
| `old_main_noctis` | Montages sombres, cinématiques et scènes à dominante noire | Noirs profonds mais non bouchés, teinte froide ou neutre, hautes lumières chaudes optionnelles |

Les paramètres ne seront pas codés en dur. Chaque profil devra exposer au minimum `contrast`, `gamma`, `highlight_rolloff`, `shadow_lift`, `saturation`, `temperature`, `tint`, `skin_protection`, `clarity`, `bloom` et `sharpen_luma`.

## Phase 3 — Recalibrer F05 LIBRARIUS FACIES

Le test précédent montre que GFPGAN peut produire un gain visible, mais son coût et son intensité deviennent élevés sur une vidéo 120 FPS. La nouvelle logique devra utiliser la détection de visage et la confiance de détection pour mélanger la restauration avec l’image d’origine.

La force de restauration sera réduite par défaut et appliquée seulement aux régions faciales. Le résultat restauré sera fusionné avec la source selon une pondération contrôlée. Les yeux et les contours pourront recevoir une pondération plus forte, tandis que la peau et les aplats recevront une pondération plus faible.

Le module devra également éviter de traiter deux fois le même visage lorsque les détections sont proches entre images. Une cohérence de boîte et de pondération devra être conservée autant que possible afin de réduire le scintillement.

## Phase 4 — Ajouter la cohérence temporelle

Après F07, contrôler la stabilité entre images. La première version pourra utiliser une approche légère : limiter les variations brusques de gain local et de couleur, puis lisser les paramètres plutôt que les pixels lorsque cela est possible.

Cette étape devra être activée seulement lorsque l’analyse F01 détecte une scène fortement animée, une lumière intermittente, des cheveux fins ou des textures répétitives. Elle restera désactivée pour les scènes simples afin de préserver la vitesse.

## Phase 5 — Tester trois variantes sur la source originale

La source `rife_input_5s.mp4` sera traitée depuis zéro. Les trois variantes auront le même F02 RIFE et les mêmes étapes de restauration, afin que la comparaison porte réellement sur le style final.

| Variante | F05 | F07 | But |
|---|---|---|---|
| A — Natural | GFPGAN faible, fondu important | `realistic_aurea` | Vérifier le détail naturel du visage et de la peau |
| B — Premium | GFPGAN moyen, masque sélectif | `hdr_imperator` modéré | Maximiser l’impact visuel sans écraser les noirs |
| C — Cinematic | GFPGAN faible à moyen | `old_main_noctis` adapté | Tester un look plus sombre et cinématographique |

Chaque résultat sera conservé sous une campagne séparée dans le Volume Modal. Les comparaisons seront faites sur les mêmes images aux secondes 1, 2, 3 et 4, avec des gros plans du visage, des cheveux, du vêtement et du décor.

## Phase 6 — Sélection et intégration

Le profil retenu ne sera pas choisi uniquement parce qu’il est le plus contrasté. Il devra obtenir le meilleur équilibre entre détail perçu, naturel du visage, lisibilité des noirs, absence de halo et stabilité temporelle.

Une fois la variante choisie, ses paramètres deviendront le profil par défaut de `cinematic_hyper_detail`. Les autres profils resteront disponibles pour les différents types de vidéos détectés par F01.

Les informations de campagne devront enregistrer le profil choisi, les paramètres numériques, la version des modèles, le nombre de visages détectés, la résolution, la cadence et les hashes des sorties.

## Phase 7 — Déploiement Modal

Le déploiement continuera à utiliser l’image Modal déjà construite et les Volumes indépendants du nouveau compte. Les modèles resteront dans `lacrimae-dev6-models`, tandis que les vidéos et les rapports resteront dans `lacrimae-dev6-video`.

Aucun secret ne devra être ajouté à GitHub ou au dépôt. Le changement de compte restera piloté par le fichier env local utilisé lors des commandes de déploiement et d’exécution.

## Décision attendue après les tests

La prochaine exécution doit produire trois sorties comparables, et non une seule sortie arbitraire. Nous pourrons alors voir si l’amélioration recherchée vient principalement de la colorimétrie, du dosage facial ou de la combinaison des deux.

Le résultat attendu de cette itération n’est pas encore de prétendre égaler Topaz ou NORAGE sur tous les contenus. Il est de construire une base mesurable et contrôlable qui explique visuellement chaque gain et chaque artefact avant d’augmenter la complexité.

## Référence publique analysée

La page publique de NORAGE annonce un `COLOR CORRECTION PACK` comprenant `HDR CC`, `OLD MAIN CC` et `REALISTIC CC`, prévu pour After Effects [1]. Les aperçus publics montrent principalement une transformation de contraste, de tonalité et de saturation, mais ne publient pas la chaîne complète de restauration vidéo [1] [2].

[1]: https://boosty.to/norage_ae "Page publique Boosty de noRAGE"
[2]: https://boosty.to/norage_ae/posts/49aec8f1-050c-48a2-ae43-834affde42b6 "Post public CC PACK PREVIEW de noRAGE"
