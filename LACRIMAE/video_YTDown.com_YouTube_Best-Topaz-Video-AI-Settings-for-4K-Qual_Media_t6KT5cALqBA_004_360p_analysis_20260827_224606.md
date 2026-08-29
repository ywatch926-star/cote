Cette analyse technique de la vidéo détaille les étapes de traitement d'image via Topaz Video AI (TVAI) et After Effects (AE).

### 1. Opérations annoncées ou visibles
*   **Logiciels :** Topaz Video AI v3.2.0 (pour l'amélioration spatiale) et Adobe After Effects (pour l'étalonnage final).
*   **Flux de travail :** Importation d'une source basse résolution -> Traitement via le modèle **Proteus** dans TVAI -> Exportation -> Application d'un "CC" (Color Correction) prédéfini dans AE.
*   **Paramètres TVAI (visibles à 02:19) :**
    *   **Modèle :** Proteus (Fine Tune/Enhance).
    *   **Mode :** Manuel.
    *   **Revert Compression :** 90 (Forte correction des artefacts de compression).
    *   **Recover Details :** 85 (Reconstruction agressive des textures).
    *   **Sharpen :** 75 (Netteté marquée).
    *   **Reduce Noise :** 55 (Réduction modérée du bruit).
    *   **Dehalo :** 5 (Léger traitement des contours doubles).
    *   **Anti-Alias/Deblur :** 50 (Équilibre entre lissage et clarté).

### 2. Indices sur l'Enhance, l'Upscale et l'Interpolation
*   **Enhance :** Opération centrale. Utilisation du modèle Proteus pour reconstruire les données manquantes à partir d'une source floue.
*   **Upscale 4K :** Bien que le menu affiche "1920x1080 (Original)" lors de la démonstration, l'objectif annoncé est le passage en "High Quality". Le modèle Proteus est ici utilisé pour la restauration de texture plus que pour un changement massif de définition.
*   **Interpolation 120 FPS :** Aucune opération d'interpolation d'images (Apollo/Chronos) n'est visible ou mentionnée. La fluidité temporelle reste celle de la source.

### 3. Changements visibles sur les composants de l'image
*   **Visage :** Reconstruction des pores de la peau et de l'éclat des yeux. Les zones d'ombre sur le visage perdent leur aspect "bloc de pixels" pour un dégradé plus lisse.
*   **Cheveux :** Les masses floues sont transformées en mèches distinctes. Augmentation significative de la micro-netteté sur les follicules.
*   **Vêtements et Textures :** Les textures de tissus (sweat à capuche) retrouvent un grain de fibre visible.
*   **Texte :** Non applicable ici, mais les bords des objets (casque de hockey à 00:26) sont plus nets.
*   **Contraste et Couleurs :**
    *   **Topaz :** Apporte une légère clarté (clarity) mais reste fidèle aux couleurs sources.
    *   **After Effects (CC) :** C'est ici que le contraste est radicalement modifié. Les noirs sont approfondis, la saturation est augmentée, et une teinte spécifique (souvent plus chaude ou typée "cinéma") est appliquée.
*   **Grain et Halos :** Le bruit numérique original est supprimé et remplacé par une texture générée par l'IA, très propre. Le réglage "Dehalo" à 5 limite l'apparition de liserés blancs autour des silhouettes sombres.

### 4. Artefacts ou limites
*   **Effet "Waxy" (Cire) :** Avec un "Recover Details" à 85 et "Reduce Noise" à 55, la peau peut prendre un aspect légèrement artificiel ou trop lisse sur certaines zones si le mouvement est rapide.
*   **Interprétation de l'IA :** Sur les sources très dégradées, l'IA "invente" des détails (comme la structure de l'iris ou des rides) qui peuvent différer légèrement de la réalité originale.

### 5. Éléments exploitables pour une cible ATOM-IC v2
*   **Priorité à la reconstruction :** Pour des sources très compressées, le ratio Revert Compression (90) > Sharpen (75) est la clé pour éviter d'accentuer les défauts.
*   **Séparation des tâches :** La vidéo démontre que l'IA doit servir à la **structure** (détails, netteté) tandis que le logiciel de post-production (AE) doit servir à l'**esthétique** (contraste, colorimétrie).
*   **Modèle Proteus :** Confirmé comme le modèle le plus polyvalent pour le "Fine Tuning" manuel grâce à ses 6 curseurs indépendants, permettant de cibler précisément les faiblesses de la source.