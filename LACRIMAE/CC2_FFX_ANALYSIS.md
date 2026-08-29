# Analyse technique du preset cc2.ffx

## Identification

Le fichier est un preset natif After Effects au format RIFF big-endian `RIFX`, d’environ 102458 octets. Il ne s’agit pas d’une simple LUT texte ni d’un fichier de paramètres facilement lisible par FFmpeg.

## Effets identifiables dans la chaîne

L’inspection des chaînes lisibles révèle une chaîne d’effets After Effects composée de :

1. `ADBE Sharpen` — accentuation de netteté.
2. `ADBE Unsharp Mask2` — masque flou avec réglage séparé de la quantité de netteté.
3. `MB LookSuite3` / `Magic Bullet Looks` — couche de look et de colorimétrie stylistique.
4. `S_Gradient` — effet Sapphire de gradient, probablement utilisé pour un overlay, une teinte, une lumière ou une transition de luminance.
5. `ADBE Effect Parade` et `ADBE Compositing Options` — structure de pile d’effets et options de composition.

Le preset contient aussi des paramètres nommés `Sharpen Amount`, `Compositing Options`, des informations de nommage d’effets et des données binaires de réglage. Les valeurs exactes ne sont pas directement interprétables de manière fiable sans After Effects ou un parseur spécifique du format FFX.

## Interprétation pour ATOM-IC v2

Ce fichier confirme que le rendu recherché peut provenir d’une pile multicouche, et pas d’une seule correction couleur. La recette observable est au minimum : netteté contrôlée → Unsharp Mask → Magic Bullet Looks → gradient/overlay Sapphire → composition finale.

La sous-frégate proposée doit donc séparer :

- `F09 AETHER COMPOSITUM` : construction de la pile de compositing.
- Preset `silver_gray` : désaturation contrôlée, contraste métallique, hautes lumières froides et noirs lisibles.
- Preset `dark` : contraste cinématique et teinte sombre sans écraser la texture des vêtements.
- Preset `warm` : tons chair protégés, hautes lumières chaudes et saturation sélective.
- Preset `viral_hdr` : overlay lumineux, contraste plus fort, glow limité et énergie accrue.
- Preset `clean_realistic` : effet minimal, priorité au naturel.

## Limites

Un fichier `.ffx` ne peut pas être appliqué directement à une vidéo headless avec FFmpeg. Il peut être chargé dans After Effects, mais dans notre infrastructure il doit servir de référence de recette. Nous devons reproduire ses opérations avec des filtres équivalents : `unsharp`, `curves`, `colorlevels`, `eq`, extraction de hautes lumières, flou, `screen`/`softlight`/`overlay`, gradient, grain et recomposition.

Le preset `cc2.ffx` est donc très pertinent : il révèle une architecture de finition plus riche que notre simple grade. Il ne suffit toutefois pas à lui seul pour expliquer la restauration faciale ou l’interpolation temporelle.

## Conclusion

`cc2.ffx` confirme que notre prochaine sous-frégate doit être une **bibliothèque de presets multicouches**, sélectionnable depuis Oracle, et non une liste de valeurs de contraste isolées. Les presets doivent rester des fichiers de configuration versionnés, avec des couches activables, des opacités contrôlées et des garde-fous contre les halos et les noirs bouchés.

Aucune modification du code v2 n’a été effectuée pendant cette inspection.
