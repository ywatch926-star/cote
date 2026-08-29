# Audit du codex fourni

Fichier audité : `pasted_file_BsSxIv_codex(5).json`.

## Résultat

Le JSON est syntaxiquement valide et sa structure principale est compatible avec le flux F03/PICTOR : `version: 4.0`, `pipeline: LACRIMAE_DEV`, un clip, une session et un bloc de séquences virtuelles matérialisées.

Le bloc `virtual_sequences` est un objet `dev4.motion-slow-sequences.v1` contenant 86 séquences, 599 frames à 59,94006 FPS, une durée cible de 9,993 secondes et des chemins `sequences/seq_XXXX_normal.mp4` ou `sequences/seq_XXXX_slow.mp4`. Les 86 entrées sont validées, dont 35 Motion Slow et 51 normales. Le mode Motion Slow est `partial`, à 0,5×, sur 3–7 secondes avec `ffmpeg_minterpolate`.

La session indique une composition verticale 1080×1920, `fit: contain`, rotation fixe à 90 degrés sur le calque vidéo, vidéo à 2,4× et fond transparent. Le preset `dark_luxury_noir` est activé à 12 % et possède une valeur de filtre CSS cohérente avec ce preset. Les valeurs sont donc présentes pour la preview et pour PICTOR.

## Points à corriger ou valider

`validated_by_magos` vaut `false`. Le codex n’est donc pas encore marqué comme validé par le Champion ; il est techniquement exploitable mais ne doit pas être considéré comme un codex final approuvé.

Le codex embarque bien les 86 séquences dans `virtual_sequences`, mais PICTOR dev4 charge encore son manifeste séparé `src/data/sequences.json` dans `Root.jsx`. Pour un rendu final F00-C, ce manifeste PICTOR doit être synchronisé avec le même artifact complet ; le codex seul ne suffit pas à garantir que PICTOR utilisera les 86 MP4.

La valeur `session.presets.contrast` vaut `1.0`, tandis que `color_css_filter` commence par `contrast(1.3)`. Comme PICTOR remplace le contraste du filtre avec la valeur numérique `contrast`, le rendu effectif peut devenir `contrast(1.0)`. Si l’intention est de conserver le contraste Dark Luxury Noir standard, la valeur numérique doit être confirmée à 1,3 ou le comportement de remplacement doit être ajusté.

## Conclusion

Le codex est **valide structurellement et cohérent pour F03 Preview**, mais **pas encore finalisé pour le gate Champion** : il faut valider le montage (`validated_by_magos: true`) et synchroniser le manifeste utilisé directement par PICTOR. Le fichier original n’a pas été modifié.
