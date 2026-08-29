# F03 PREVIEW — TRACKING (récupération & correctifs)

> Date : 2026-08-08

## Contexte

Le code source du preview `F03_PREVIEW/CODEBASE` a été perdu après un reset du
sandbox (jamais poussé sur GitHub). Il a été **entièrement récupéré** depuis le
sandbox d'origine encore vivant, via son serveur Vite :
`https://5173-7b5fcbca1aa0247f.monkeycode-ai.live`

Sources originales extraites depuis les sourcemaps embarquées par Vite
(`sourcesContent`) — fichiers propres, pas du code transformé.

## Fichiers récupérés

```
src/App.jsx                  (829 lignes)
src/main.jsx
src/preview/OmniComposition.jsx   (548 lignes)
src/preview/BloomText.jsx         (303 lignes)
public/codex.json
public/clip_001.mp4               (11,3 Mo — 1920x1080)
public/logo.png                   (4,2 Mo)
public/backgrounds/               (7 PNG + manifest.json)
package.json / index.html / vite.config.js
```

## Correctifs appliqués

### 1. confirmLogoPlacement (App.jsx) — BUG PRINCIPAL
Trois `updateSession('logo', …)` séquentielles lisaient le même `session`
obsolète (closure) et React les batchait : seule la dernière (`y_pct`) survivait.
`position: 'custom'` et `x_pct` étaient **perdus** → le logo restait à son
preset. Remplacé par une **mise à jour atomique** via `setSession(s => …)`.

### 2. Priorité du logo (OmniComposition.jsx)
`logo={clip.logo || session.logo}` → `logo={session.logo || clip.logo}`.
Dès qu'un clip définissait un `logo`, les réglages de session (custom) étaient
ignorés.

### 3. logo.png
Le fichier était absent de la copie locale (404 → « image cannot be decoded »).
Récupéré depuis le sandbox.

## Vérification E2E (puppeteer, headless chromium)

Flux : double-clic vidéo → modal → Oui → position custom.
- Modal ouverte : OK
- Marqueur au point cliqué (70 / 29.8) : OK
- Select position → `custom` : OK
- Codex exporté : `session.logo = { position: 'custom', x_pct: 70, y_pct: 29.8 }` : OK

## Améliorations (2026-08-08)

### 4. Onglet « 🎬 Vidéo » + centrage vertical (session)
Nouvel onglet dédié (pour accueillir d'autres particularités vidéo). Slider
`session.video.offset_y` (-20 % à +20 %, pas de 0,5) appliqué en
`translateY(%)` au `<Video>` (OmniComposition L2). Réglage **session** →
appliqué à tous les clips (règle). `+` = bas, `-` = haut.

### 5. Échelle du logo élargie
Slider « Taille du logo » : `max` 60 → **90** (= 1,5 × l'ancien max). Min 5
conservé, pas 1. `LogoOverlay` gère déjà `width_pct` en % de la largeur.

## Vérification E2E (suite)
- Balise (régression) : OK
- Onglet Vidéo : présent, offset → `-12.5 %` reflété dans le label
- Export : `session.video.offset_y = -12.5` + `session.logo` custom conservés
- Slider logo `min=5 max=90` : OK

## Points d'attention (non corrigés, à trancher)

- **Ratio incohérent** : `clip_001.mp4` est du 1920x1080 (16:9 paysage) mais le
  codex le déclare 1080x1920 (9:16 portrait). Rendu en `object-fit: cover`
  (recadré). Le mapping clic→logo reste cohérent, mais le cadrage vidéo est à
  valider côté pipeline.
- **Zoom** : le logo est posé en % de la composition, il ne suit pas le zoom /
  pan de la vidéo (`zoom_keyframes`). Choix à valider.
- Le preview n'est **pas poussé sur GitHub** (commit à faire).
