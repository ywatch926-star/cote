# Références Real-ESRGAN — F04_UPSCALE

## Sources officielles consultées

1. [Dépôt officiel xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) — licence BSD-3-Clause ; décrit Real-ESRGAN comme un moteur de restauration/super-résolution pour scènes générales et liste les modèles x4plus, anime et vidéo.
2. [Script officiel d’inférence Python](https://github.com/xinntao/Real-ESRGAN/blob/master/inference_realesrgan.py) — définit `RealESRGAN_x4plus`, son architecture RRDBNet, l’URL officielle du poids `https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth`, le tuilage et `outscale`.
3. [Article Real-ESRGAN](https://arxiv.org/abs/2107.10833) — décrit la super-résolution aveugle pour images réelles et l’entraînement sur dégradations synthétiques.

## Modèle validé

- Identifiant : `realesrgan-x4plus-0.1.0`
- Source : release officielle GitHub v0.1.0
- SHA-256 : `4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1`
- Taille : 67,040,989 octets
- Volume Modal : `lacrimae-dev6-models`
- Chemin : `models/RealESRGAN/0.1.0/RealESRGAN_x4plus.pth`
- Politique F04 : modèle x4 exécuté avec `outscale=2` pour convertir 1920x1080 vers 3840x2160, avec tuilage 512 et padding 16.

## Compatibilité appliquée

BasicSR 1.4.2 utilise un ancien chemin `torchvision.transforms.functional_tensor`. Le worker crée un alias vers `torchvision.transforms.functional` avant d’importer Real-ESRGAN, afin de rester compatible avec torchvision 0.20.1.
