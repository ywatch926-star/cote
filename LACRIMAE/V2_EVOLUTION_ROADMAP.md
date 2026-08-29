# LACRIMAE v2 — Chantier d’évolution

La branche `v2` est une copie exacte du commit stable `4c0a7a9` de `dev6`. La branche `dev6` ne doit plus recevoir d’expérimentation visuelle risquée.

## Priorité 1 — Reconstruction naturelle du détail

Réduire l’aspect de simple sharpening en ajoutant une séparation nette entre le détail réellement présent et le détail reconstruit. Le visage doit être traité par masque et fondu avec la source, tandis que cheveux, vêtements, texte et décor doivent recevoir une restauration générale plus légère.

## Priorité 2 — Finition couleur contrôlée

Conserver F07 CHROMA DOMINATUS, mais calibrer trois profils sur des images fixes et des extraits courts. HDR Imperator sert de référence d’impact, Realistic Aurea de référence naturelle et Old Main Noctis de référence sombre. Les noirs ne doivent pas être bouchés et les hautes lumières doivent rester lisibles.

## Priorité 3 — Cohérence temporelle réelle

F08 doit évoluer de son mode garde transparente vers une stabilisation temporelle sélective. Toute réduction de scintillement devra préserver les contours et éviter le ghosting sur les yeux, les mains, les cheveux et les textes.

## Priorité 4 — Validation reproductible

Chaque essai doit partir de la même source originale, conserver la résolution native et produire un rapport avec profil, cadence, nombre d’images, durée, audio, hash et paramètres. Aucun résultat déjà modifié ne doit servir d’entrée à une comparaison de profil.

## Règle de sécurité

Avant toute modification importante, créer un commit v2 identifiable. En cas de régression, revenir au commit précédent de v2 ; `dev6` reste la référence fonctionnelle et ne doit pas être réécrit.
