# Choix des modèles de restauration faciale — 2026-08-26

## CodeFormer
Source officielle : https://github.com/sczhou/CodeFormer
Le dépôt se présente comme une méthode de restauration faciale aveugle basée sur un Codebook Lookup Transformer (NeurIPS 2022). Le dépôt contient un script d’inférence, un répertoire de poids et une licence. CodeFormer est adapté à une restauration faciale ciblée, mais son résultat peut reconstruire des détails et ne doit donc être appliqué que dans des masques de visages suffisamment grands et avec un réglage de fidélité contrôlé.

## GFPGAN
Source officielle : https://github.com/TencentARC/GFPGAN
Le dépôt décrit GFPGAN comme un algorithme pratique de restauration de visages réels, utilisant des priors de visage issus d’un GAN préentraîné. Une release v1.3.8 est visible dans le dépôt. GFPGAN est également ciblé visage et ne doit pas être appliqué aux vêtements, voitures, monstres ou décors.

## Décision MVP
La première restauration faciale doit être optionnelle et masquée. Il faut d’abord détecter les visages, vérifier leur taille et leur confiance, puis appliquer CodeFormer ou GFPGAN uniquement aux crops faciaux. Aucun modèle facial n’est encore installé dans LACRIMAE dev6 au moment de cette note. La restauration générale et la finition restent séparées.

## NAFNet et restauration générale
Source officielle : https://github.com/megvii-research/NAFNet
Le dépôt officiel décrit NAFNet comme une implémentation PyTorch de restauration d’image, avec des résultats annoncés sur le défloutage GoPro et le débruitage SIDD. Il est pertinent comme piste de restauration générale, mais son intégration vidéo nécessite encore de choisir un checkpoint et de mesurer le débit sur GPU Modal. Il n’est pas téléchargé dans le Volume modèles à ce stade.

## Licences
GFPGAN est publié sous Apache License 2.0 selon son dépôt officiel. CodeFormer indique une licence NTU S-Lab License 1.0 ; son usage et sa redistribution doivent respecter cette licence. La décision MVP actuelle privilégie GFPGAN v1.3 pour un premier test facial ciblé ; son poids officiel est déjà dans `models/GFPGAN/1.3/GFPGANv1.3.pth` avec hash `c953a88f2727c85c3d9ae72e2bd4846bbaf59fe6972ad94130e23e7017524a70`.

## Sources consultées
- https://github.com/sczhou/CodeFormer
- https://github.com/TencentARC/GFPGAN
- https://github.com/megvii-research/NAFNet
- https://raw.githubusercontent.com/sczhou/CodeFormer/master/README.md
- https://raw.githubusercontent.com/TencentARC/GFPGAN/master/README.md
