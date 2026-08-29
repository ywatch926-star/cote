# Dark Luxury Noir — implementation dev4

Le preset **Dark Luxury Noir** a été intégré à F03 Preview avec un seul curseur d’intensité de 0 à 100 %. Le sélecteur de preset et le curseur sont disponibles dans l’onglet Effets.

À 0 %, l’effet est désactivé. À une valeur positive, la composition applique une base monochrome chaude, une désaturation progressive, un contraste renforcé et un halo champagne/rouge/violet. La valeur est stockée dans `session.presets.dark_luxury_noir` et exportée par le codex.

La composition PICTOR possède le même helper de calcul et le même overlay. Le rendu final lit donc la même valeur du codex. F00-C et le Motion Slow ne sont pas modifiés.

## Vérification navigateur

F03 Preview a chargé les deux séquences F00-C et affiche une timeline d’environ 2,8 secondes pour la revue locale. Le preset `Dark Luxury Noir` a été sélectionné à 100 %, puis le curseur a été réglé à 50 %. L’interface affiche bien `Dark Luxury Noir : 50 %` et l’image est visiblement transformée.

## Vérifications techniques

- Build Vite F03 réussi.
- `npm run check` PICTOR réussi ; composition `LacrimaeShort` détectée en 599 frames à 59,94 FPS.
- `git diff --check` réussi.
- Les fichiers de répétition des deux assets restent des artefacts de revue locale et ne doivent pas être commités comme assets de production.
