# F03 PREVIEW — dev4

F03_PREVIEW est la salle de contrôle interactive qui permet de voir le Short avant son rendu final. Elle utilise Vite, React et Remotion Player. Dans le flux dev4, elle lit le manifeste matérialisé et les petits fichiers MP4 validés par F00-B ; elle conserve un retour compatible vers les anciens manifestes virtuels.

## Entrées

```text
CODEBASE/public/video_source.mp4
CODEBASE/public/sequences.json
CODEBASE/public/sequences/seq_XXXX.mp4
CODEBASE/public/codex.json
```

Lorsque `sequences.json` possède `schema_version: dev4.materialized-sequences.v1` et `materialized: true`, chaque cut utilise le fichier indiqué par son champ `file`. F03 ne recherche donc pas une position distante dans la vidéo source pendant la lecture. La vidéo source reste disponible pour les anciens manifestes `dev4.virtual-sequences.v1`.

## Lancement

```bash
cd F03_PREVIEW/CODEBASE
npm ci
npm run dev
```

## Validation

L’interface permet de vérifier l’ordre des séquences, le rythme du Fast Match Cut, le cadrage, la rotation, le logo et les presets visuels. Les contrôles de format, luminosité, contraste, saturation, netteté, zoom, vignette et colorimétrie sont appliqués à la composition. Le texte et les flashs sont désactivés par défaut dans le preset actuel. L’export du `codex.json` conserve la session et les réglages validés par le Champion.

F03 ne choisit pas les séquences et ne les extrait pas. F00-A propose le plan ; F00-B crée et valide les fichiers ; F03 sert à contrôler la composition et les réglages avant rendu.

## Contrat avec F00 et PICTOR

```text
F00-A/OUT/sequences_plan.json
              │
              ▼
F00-B/OUT/sequences.json + sequences/*.mp4
              │
              ├──► F03_PREVIEW : aperçu et réglages
              │                    │
              │                    ▼
              └──────────────► PICTOR : rendu final
```

F03_PREVIEW et F03_PICTOR utilisent la même composition Remotion, le même codex et le même manifeste. La preview sert à visualiser et valider ; PICTOR sert à rendre le MP4 final sans refaire la sélection.

## Composition et transformations

Le codex peut définir une composition `vertical` (1080×1920), `horizontal` (1920×1080) ou `square` (1080×1080). La vidéo peut être adaptée avec `fit: cover` ou `fit: contain`. Le background est optionnel et peut être désactivé ; dans le preset de test actuel, seul le contenu vidéo et le logo sont visibles.

Les rotations sont définies dans `session.composition`. `rotation_mode: per_sequence` ajoute `rotation_step_deg` à chaque séquence ; `rotation_mode: continuous` interpole jusqu’à `rotation_total_deg` sur la durée. `rotation_layer` vaut `video` pour garder textes et logo droits, ou `composition` pour faire tourner l’ensemble des calques. Ces paramètres sont exportés dans le codex et réutilisés par PICTOR.

## Motion Slow optionnel

F03 peut charger automatiquement `public/motion_slow_manifest.json` lorsqu’il est présent. Ce manifeste est prioritaire sur `sequences.json` et permet de visualiser les séquences normales et les séquences interpolées produites par F00-C. En son absence, F03 revient automatiquement au manifeste normal de F00-B.

Le panneau **Vidéo** expose les choix `Normal`, `Partiel` et `Global`, la vitesse 0,75×, 0,5× ou 0,25×, les plages en secondes et le moteur sélectionné. Ces réglages sont enregistrés dans le `codex.json` exporté ; ils ne lancent pas F00-C depuis le navigateur. Le traitement est déclenché séparément par le workflow GitHub Actions F00-C, uniquement à la demande de l’opérateur.

Le mode Normal reste la référence. Une fois l’artifact F00-C produit, ses fichiers `sequences/*.mp4` peuvent être copiés dans `public/sequences/` avec `motion_slow_manifest.json` pour effectuer la revue visuelle dans F03 avant PICTOR.

## Preset Dark Luxury Noir

L’onglet **Effets** propose le preset `Dark Luxury Noir` avec un unique curseur d’intensité de `0 %` à `100 %`. À `0 %`, l’effet est désactivé ; à `100 %`, il combine contraste renforcé, désaturation monochrome, chaleur champagne/bronze, noirs profonds et halo sélectif rouge/violet.

La valeur est enregistrée dans `session.presets.dark_luxury_noir` lors de l’export du `codex.json`. La composition PICTOR utilise la même clé et le même calcul de filtre afin que le rendu final corresponde au réglage validé dans F03. Le Motion Slow F00-C reste indépendant.
