# Diagnostic F04_UPSCALE — 25 août 2026

## Résumé

L’intégration Real-ESRGAN x4plus fonctionne jusqu’au chargement du modèle et à l’inférence sur GPU Modal L4. Le traitement séquentiel frame par frame n’est toutefois pas exploitable économiquement pour une vidéo 120 FPS : 597 frames à 1920×1080 nécessitent chacune une inférence x2 avec tuilage, et le run n’a pas terminé après plusieurs fenêtres d’attente de 120 secondes.

## Runs observés

| Run | Entrée | Tuilage | Résultat |
|---|---|---:|---|
| upscale-test-002 | 597 frames, 1080p/120 FPS | 256, 40 tuiles/frame | Arrêté préventivement ; progression sans erreur mais trop lente |
| upscale-test-003 | 597 frames, 1080p/120 FPS | 512, 12 tuiles/frame | Arrêté préventivement ; amélioration du nombre de tuiles, mais durée encore excessive |
| upscale-test-004 | 120 frames, 1080p/120 FPS, 1 seconde | 512, 12 tuiles/frame | Arrêté préventivement après plusieurs minutes ; aucune exception d’inférence observée |

## Conclusion technique

Le problème est la granularité de l’implémentation, non la présence du modèle, le Volume ou la compatibilité CUDA. F04 doit être accélérée par traitement par lots, conversion TensorRT/ONNX si stable, ou découpage parallèle par segments avec limitation de concurrence. L’audio n’est pas encore copié dans F04. La sortie finale 4K/120 n’est donc pas encore validée.

## Modèle

`RealESRGAN_x4plus.pth`, release officielle v0.1.0, SHA-256 `4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1`, stocké dans `models/RealESRGAN/0.1.0/` du Volume `lacrimae-dev6-models`.
