# Recherche F00-C Motion Slow

## Sources consultées

- FFmpeg Filters Documentation: https://ffmpeg.org/ffmpeg-filters.html
- ECCV2022-RIFE: https://github.com/hzwer/ECCV2022-RIFE
- RIFE ncnn Vulkan: https://github.com/nihui/rife-ncnn-vulkan

## Conclusions

FFmpeg fournit le filtre `minterpolate`, adapté à une première solution CPU et simple à intégrer dans GitHub Actions. Il convertit vers une fréquence d’images cible par interpolation de mouvement et propose une détection des changements de scène. C’est la solution la plus simple à déployer, mais elle peut produire des artefacts sur les mouvements rapides, les croisements et les cuts courts.

RIFE est une solution d’interpolation par réseau neuronal. Le dépôt ECCV2022-RIFE indique un fonctionnement par paires d’images et une interpolation 2x, avec une commande vidéo et une exécution possible dans Docker. Le dépôt `rife-ncnn-vulkan` fournit des exécutables et modèles Linux/Windows/macOS, sans dépendance CUDA/PyTorch obligatoire, avec un mode CPU `-g -1` et un mode GPU Vulkan. Cette solution est plus proche d’un rendu de type Twixtor, mais elle est plus lourde et plus lente sur runner CPU.

## Recommandation

Pour F00-C, prévoir une abstraction `engine` contrôlable par l’opérateur : `ffmpeg_minterpolate` comme moteur par défaut et `rife_ncnn` comme moteur qualité optionnel. Le premier test réel doit commencer avec FFmpeg pour valider le contrat, les plages partielles et les transitions. RIFE pourra ensuite devenir le moteur haute qualité si le test visuel montre que `minterpolate` ne suffit pas.

F00-C doit rester optionnelle et recevoir explicitement un mode `off`, `partial` ou `global`, avec une vitesse et des plages temporelles. Aucun traitement ne doit être lancé si l’opérateur ne l’active pas.

## Références

[1]: https://ffmpeg.org/ffmpeg-filters.html "FFmpeg Filters Documentation"
[2]: https://github.com/hzwer/ECCV2022-RIFE "ECCV2022-RIFE"
[3]: https://github.com/nihui/rife-ncnn-vulkan "RIFE ncnn Vulkan"

Auteur : Manus AI
Date : 2026-08-24

