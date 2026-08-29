# ATOM-IC — Stratégie de domination visuelle pour DOMINUS HYPERFLUIDA

## 1. Position de départ

Les trois références analysées montrent que le résultat recherché ne vient pas principalement de la 4K et ne vient pas principalement du nombre d’images par seconde. Les cadences mesurées sont différentes — une référence à 30 FPS et deux références à 60 FPS — alors que leur apparence partage une même signature esthétique. Cela signifie que la cadence peut améliorer le mouvement, mais qu’elle n’explique pas à elle seule le rendu premium.

La résolution n’explique pas davantage le résultat. Les références utilisent des dimensions différentes, dont du 720×1280, du 1080×1920 et du 720×866, tout en conservant une impression de détail et de puissance visuelle. Le facteur commun est donc principalement perceptuel : l’œil reçoit une image dont les contours, les textures, les couleurs, les lumières et la séparation des plans sont beaucoup plus intenses que dans une vidéo simplement réencodée.

Notre sortie actuelle a validé le transport technique — 120 FPS, format conservé, audio conservé, restauration générale et finition — mais elle n’a pas encore reproduit cette signature. La raison est claire : nous avons utilisé des filtres modérés et GFPGAN sur les visages, alors que les références appliquent une transformation globale de l’image.

## 2. Définition de X

Dans ATOM-IC, **X** ne doit pas être défini comme « résolution » ou « fluidité ». X est la **densité de détail perçue sous contrainte de cohérence**.

On peut la représenter ainsi :

> **X = détail lisible × séparation des plans × énergie lumineuse × cohérence temporelle × cohérence stylistique − artefacts**

Cette formule n’est pas une mesure scientifique unique ; c’est une fonction d’objectif pour guider le pipeline. Elle explique pourquoi une vidéo 720p peut paraître plus travaillée qu’une vidéo 4K plate, et pourquoi une vidéo 120 FPS peut rester visuellement médiocre si ses textures sont molles, ses couleurs ternes ou ses contours mal définis.

| Terme de X | Signification visuelle | Exemple dans les références |
|---|---|---|
| Détail lisible | Les textures importantes restent visibles sans devenir du bruit | Cheveux, vêtements, métal, ailes, roche, eau |
| Séparation des plans | Le sujet se détache clairement de l’arrière-plan | Silhouette nette, profondeur renforcée |
| Énergie lumineuse | Les sources lumineuses ont du volume et une hiérarchie | Lasers, ciel, explosions, lumières cyan |
| Cohérence temporelle | Le détail reste stable d’une frame à l’autre | Pas de scintillement ni de texture qui nage |
| Cohérence stylistique | Toutes les scènes appartiennent au même univers visuel | Palette cyan/bleu, accents chauds, noirs profonds |
| Artefacts | Déformations, halos, visages plastiques, textures répétées | Pénalité qui annule le gain perceptuel |

Le créateur des références ne gagne probablement pas grâce à un seul « modèle magique ». Il gagne en contrôlant simultanément plusieurs composantes de X, surtout sur les éléments que le regard humain remarque en premier : silhouettes, visages, lignes de mouvement, lumière, couleurs et objets centraux.

## 3. A — Analyse subatomique

L’atome du problème n’est pas le fichier MP4. L’atome est une combinaison locale de pixels et de mouvement : un bord de visage, une mèche de cheveux, une couture, une plaque métallique, une aile, une particule d’explosion ou le contour d’un laser.

Chaque zone possède une fonction visuelle différente. Un visage a besoin de fidélité et de douceur contrôlée. Un vêtement a besoin de texture et de continuité. Un véhicule ou un bâtiment a besoin de lignes et de micro-contraste. Une explosion a besoin de séparation entre le noyau lumineux, la fumée et les particules. Appliquer le même filtre à toute la frame est donc une erreur de conception.

L’analyse subatomique doit produire une carte de salience : quelles zones doivent être nettes, quelles zones doivent rester douces, quelles zones portent la lumière, et quelles zones sont trop pauvres pour être restaurées sans hallucination.

| Région | Priorité | Risque si le traitement est trop fort |
|---|---:|---|
| Visage humain | Très haute | Peau plastique, yeux faux, identité modifiée |
| Yeux et bouche | Très haute | Déformation immédiatement visible |
| Cheveux et barbe | Haute | Motifs artificiels et scintillement |
| Vêtements | Moyenne à haute | Texture répétitive ou contours trop durs |
| Métal et architecture | Haute | Halos, lignes cassées, bruit accentué |
| Végétation et fumée | Moyenne | Bruit mouvant et détails inventés instables |
| Lasers et explosions | Haute pour le style | Bloom excessif et écrasement des hautes lumières |
| Arrière-plan flou | Faible | Sur-accentuation qui attire le regard au mauvais endroit |

## 4. T — Transmutation inventive et contradictions TRIZ

La première contradiction est : **plus de détail contre moins d’artefacts**. Un filtre agressif augmente immédiatement l’impression de netteté, mais il révèle aussi les défauts de compression et les contours faux. La solution n’est pas de choisir entre douceur et agressivité ; c’est de séparer les zones et d’appliquer une intensité différente à chacune.

La deuxième contradiction est : **modèle spécialisé contre vidéo universelle**. Un modèle facial fonctionne bien sur un visage humain, mais ne doit pas toucher un monstre, une voiture ou une texture de décor. La solution est l’activation conditionnelle par détection et masques.

La troisième contradiction est : **qualité contre coût GPU**. Traiter chaque pixel avec plusieurs modèles lourds est prohibitif. La solution est d’utiliser un traitement global léger, puis de réserver les modèles lourds aux petites régions salientes : visage, sujet principal, objet central ou zone de texte.

La quatrième contradiction est : **style fort contre fidélité**. Les références ne sont pas neutres ; elles amplifient les couleurs et les contours. Une reproduction fidèle de la source ne suffit donc pas. La solution est d’ajouter un profil stylistique contrôlé, séparé de la restauration factuelle.

La cinquième contradiction est : **120 FPS contre stabilité des textures**. L’interpolation augmente le nombre de frames, mais elle peut amplifier les erreurs temporelles. La restauration et le sharpen doivent donc être temporellement stables : aucun traitement qui fasse scintiller les cheveux, les feuilles, les particules ou les détails de costume.

## 5. O — Optimisation cinétique et Pareto

Les leviers les plus rentables ne sont pas forcément les plus lourds. Pour approcher rapidement le rendu des références, les cinq priorités suivantes devraient produire la plus grande partie du gain visuel :

| Priorité | Levier | Impact attendu | Coût |
|---:|---|---:|---:|
| 1 | Profil de contraste et colorimétrie par scène | Très élevé | Faible |
| 2 | Netteté edge-aware et micro-contraste sélectif | Très élevé | Faible à moyen |
| 3 | Bloom et gestion des hautes lumières | Élevé | Faible |
| 4 | Restauration générale légère et stable | Élevé | Moyen |
| 5 | Restauration faciale masquée | Élevé sur les plans humains | Élevé localement |
| 6 | Interpolation RIFE 120 FPS | Élevé pour le mouvement | Déjà validé |
| 7 | Upscale 4K | Faible à moyen selon écran | Très élevé |

La conclusion Pareto est nette : **la 4K doit rester secondaire**. Avant de payer le coût d’un upscale quatre fois plus lourd, il faut obtenir le style avec les contrastes, la lumière, le détail local et la stabilité temporelle. Le créateur des références semble gagner l’essentiel de son impact dans ces zones.

## 6. M — Manifestation N.U.K.E.

N.U.K.E. devient la couche d’exécution de DOMINUS HYPERFLUIDA, et non un simple script qui enchaîne aveuglément des modèles.

**N — Nucleus :** Oracle conserve un contrat unique. Une mission contient l’entrée, le FPS cible, le profil visuel, le niveau de restauration, la politique audio et les seuils d’artefacts.

**U — Unconventional :** les modèles lourds ne sont pas appliqués uniformément. La frégate traite globalement avec des opérations légères et concentre l’IA sur les zones détectées comme visuellement importantes.

**K — Kinetic :** le traitement est exécuté par lots et par segments, avec cache des sorties intermédiaires. Un échec F05 ne force pas à recommencer F02.

**E — Exponential :** chaque sortie produit un rapport mesurable : temps, nombre de visages, variation de contraste, nombre de frames, hash, audio, et indicateurs d’artefacts. Ces rapports servent à améliorer automatiquement le profil suivant.

## 7. Architecture cible de la frégate

> **DOMINUS HYPERFLUIDA = analyse + mouvement + restauration + style + récupération.**

| Sous-frégate | Fonction dans ATOM-IC |
|---|---|
| F00 PORTA_INGRESSUS | Détecter le format, le FPS, l’audio et la structure de l’entrée |
| F01 AUSPEX_OCULUS | Construire la carte de salience, les scènes et les masques |
| F02 MOTUS_RIFE | Interpoler vers 120 FPS ; noyau déjà validé |
| F03 APOTHECA_RESTAURA | Réduction de bruit et récupération générale douce |
| F04 FORGE_TEXTURA | Détail local des textures, vêtements, métal, végétation et décors |
| F05 LIBRARIUS_FACIES | GFPGAN/CodeFormer uniquement sur les visages humains exploitables |
| F06 LUMEN_IGNIS | Contraste, couleur, netteté, bloom et style global |
| F10 CUSTOS_RESTITUTIO | Vérification, récupération par Oracle et archivage du résultat |

Le cœur nouveau n’est pas d’ajouter le plus grand nombre de modèles. C’est de faire communiquer ces sous-frégates par une carte de salience et un profil visuel commun.

## 8. Ce que nous devons viser en premier

Le premier objectif mesurable ne doit pas être « 4K » ni « le plus grand nombre de modèles ». Il doit être : **sur la même vidéo source, un observateur préfère clairement la version LACRIMAE à la version originale, sans remarquer de visages déformés ni de textures qui scintillent**.

Le test A/B doit comparer quatre versions : source, RIFE seul, RIFE + restauration, et RIFE + restauration + profil `CINEMATIC_HYPER_DETAIL`. Les frames doivent être comparées dans les zones salientes : visage, vêtement, objet principal, arrière-plan et source lumineuse.

Un bon résultat doit améliorer simultanément la lisibilité des contours, la richesse apparente des textures, la profondeur du contraste et l’énergie des couleurs. Si le spectateur remarque d’abord l’effet du filtre au lieu du sujet de la vidéo, l’intensité est trop élevée.

## 9. Conclusion

La clé X est donc la suivante :

> **Le niveau recherché ne vient pas d’un seul modèle, mais de la coordination entre mouvement, détail local, séparation des plans, lumière, colorimétrie et stabilité temporelle.**

Nous ne devons pas chercher à battre les références avec une résolution supérieure ou une cadence supérieure. Nous devons les battre sur la **densité de détail perçue**, la cohérence et la signature visuelle. Notre avantage est de transformer cette logique en pipeline headless, reproductible et adaptatif : une seule frégate principale, des sous-frégates spécialisées, des masques, des profils, des rapports et une boucle d’amélioration.

Aucune modification de code n’est incluse dans ce document. Il s’agit du cadre de réflexion à valider avant d’implémenter la prochaine génération de la frégate.
