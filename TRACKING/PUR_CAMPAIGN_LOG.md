# LACRIMAE dev10 — JOURNAL DE CAMPAGNES PUR

| Date | Pack | Angle | Segment (s) | Canvas | Gates G0-G3 | P1 Preview | P2 Rendu | Run CI | Décision |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-09 | pur-A01 | A01 | 737.48 → 767.48 | 9:16 | G0 ✓ G1 ✓ G2 ✓ G3 ✓ (automatiques, script) | ❌ NON VALIDÉE | ⚠️ brouillon technique — lac_pur_final.mp4 12.6 Mo, 857/857 frames | [34340044745](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34340044745) | **TEST TECHNIQUE LANCÉ SANS AUTORISATION OPÉRATEUR — NON VALIDÉ.** Artefact à considérer comme brouillon jusqu'à visualisation et décision du Warsmith |
| 2026-09-12 | pur-A01 | A01 | durée complète | 9:16 | G0 ✓ G1 ✓ G2 ✓ G3 ✓ | n/a (CI direct) | ✅ VALIDÉ — pur_A01_finale.mp4 19,3 Mo, 28,6 s | [34686817585](https://github.com/jfbjfojfonf/LACRIMAE/actions/runs/34686817585) | **RUN VERT — fix staticFile() (d9ba0dc). Décisions du jour : swell continu + flash blanc 5 f + garde-fou speed >1.03 (voir PERTURABO_NOTE_2026-09-12)** |
| 2026-09-12 | pur-TOUT (A01+A02+A03) | A01, A02, A03 | 30s × 3 | 9:16 | A01 ✓ A02 ✓ A03 ✗ G2 (31.35s≠30s) | n/a (CI direct) | ❌ A03 absent — bundle refusé | [34721632577](https://github.com/jfbjfojfonf/LACRIMAE/actions/runs/34721632577) | **Loterie keyframes Twitch. Fix : G2 re-découpe locale ≤ +3s. Speed 1.05 maintenu (décision opérateur).** |
| — | — | — | — | — | — | — | — | — | — |

### Journal technique (2026-09-10)

- **Fix récupération clips (`f00_pur.py`)** : `find_downloaded_file()` ne
  considère plus que le fichier au stem exact téléchargé + purge des
  fichiers périmés au même stem avant chaque G1 (bug du 2026-09-10 :
  `reveal_02.mp4` périmé retenu à la place du segment frais ; ancien
  `pur_A01.mp4` de 4-6 s faisant échouer G2).
- **Fix clip tronqué** : `pur_A01.mp4` (2,88 Mo) était une copie interrompue
  (moov atom absent → vidéo invisible en preview) ; re-copié depuis le fichier
  complet `pur_A01` (5,33 Mo, h264 1920×1080 30,2 s @60fps).
- **Panneaux de configuration F03 (style_params)** : nouveau bloc
  `style_params` dans `dev10.pur.v1` (racine = réglages du style,
  `narrative.overlay.style_params` = réglages du texte). Panneaux éditeur :
  🎨 TEXTE OVERLAY (couleurs par ligne, police, fond case à cocher + couleur
  + opacité, contour couleur + épaisseur, taille, position X/Y), 🌫️ BLUR
  (degré, tailles fond/devant), ✂️ SPLIT (taille vidéo HAUT, taille élément
  BAS, taille/position du texte), 🎯 REFRAMING (échelle, décalage X/Y),
  🛡️ ANTI-DÉTECTION (miroir, vitesse, zoom respiration, crop).
- **Rendu par style** : `_purPackComposition.jsx` implémente les 4 mises en
  page (blur dual-layer, split top/bottom, reframing scale+offset, fullscreen)
  — miroir F04 synchronisé (`purPackCompilation.js` + `_purPackComposition.jsx`).
  Les réglages opérateur survivent à la reconversion d'un pack.

### Historique des runs CI (2026-09-09)

| Run | Résultat | Cause échec / note |
|---|---|---|
| [34338334121](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34338334121) | ❌ failure | codex injecté dans public/ au lieu de src/data/ → rendu sur route reveal (404 reveal_01.mp4). Fix a6b07f8 |
| [34339647085](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34339647085) | ❌ failure | codex.json committé avec clips[] vide → IndexError injection. Fix 4c7e524 |
| [34340044745](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34340044745) | ✅ success (technique) | Pack pur_A01 → yt-dlp → BridgeClipper → Remotion → 12.6 Mo. **⚠️ Déclenché par l'agent sans GO explicite de l'opérateur — procédure à ne pas reproduire : tout run CI réel exige l'autorisation préalable du Warsmith** |

Fixes notés pendant la mise en service : input `canvas` en string (le type choice avec « : » bloque le dispatch API), SFX désactivés par défaut (`sfx_available`, fichiers sfx/*.mp3 pas encore embarqués).

### Décisions Warsmith (2026-09-10) — texte overlay v2

- **ABROGATION** de la règle « jamais de texte pendant le hook 0-3 s » :
  le texte overlay sera statique du début à la fin, au même endroit
  (référence visuelle : capture TikTok Aishah Sofey — boîte blanche, 3
  lignes, casse mixte). Plan d'implémentation :
  `TRACKING/PUR_TEXT_IMPLEMENTATION.md` (phases A-E, non implémenté à ce
  jour — constat du bug « 6 lignes » : débordement des 2 lignes du pack à
  taille fixe). La position de la vidéo nette (blur) sera un curseur
  opérateur, pas un placement automatique.

### Implémentation texte v2 (2026-09-10) — FAIT

Phases A-E de `PUR_TEXT_IMPLEMENTATION.md` livrées :
- Texte statique début→fin (plus de hook sans texte, plus de pop_in)
- Auto-fit : 1 ligne = 1 ligne visuelle (mesure Canvas côté preview, ratio
  0.62 conservateur côté rendu Node), max 3 lignes, min 28 px
- Boîte coins arrondis + padding réglables ; preset « Référence TikTok »
  (boîte blanche, texte noir, Montserrat, size 44, sans contour)
- Casse mixte par défaut (toggle MAJUSCULES)
- Blur : curseur position verticale de la vidéo nette (fg_y_pct)
- pur_manifest.json régénéré avec le preset TikTok appliqué
- Miroir F04 synchronisé (purPackCompilation.js + _purPackComposition.jsx)

### Fix codex de base (2026-09-10) — FAIT

- `exportCodex` corrigé : review_mode racine toujours synchronisé avec le
  mode actif (pur_pack inclus), pur_manifest racine rempli, session de
  clips[0] cohérente avec la racine, clips[] ne perd plus rien si vide.
- `public/codex.json` régénéré : base PUR propre = réglages opérateur
  validés (size 39, Y 14, padding 25, blur fg 49 % @ 54 %) ; les anciens
  blocs Spider-Man ranking archivés dans clips[0].ranking_manifest.
- Police Montserrat ExtraBold embarquée (OFL, JulietaUla) :
  `public/fonts/Montserrat-ExtraBold.ttf` dans F03 et F04 + loader
  `ensurePurFont()` — parité preview/rendu au pixel.
- Le codex de base sert de référence aux prochaines vidéos PUR.

## Règle d'exploitation (ajoutée après incident du 2026-09-09)

**Aucun run CI réel (dispatch, render, consommation de minutes Actions) ne doit être
déclenché sans le GO explicite de l'opérateur.** Les gates G0-G3 sont des contrôles
automatiques de code : elles ne valident rien de créatif. La validation P1 (preview),
le rendu P2 en conditions réelles et la décision finale appartiennent au Warsmith seul.

## Règle de comparaison

Conserver toujours l'overlay du pack (copywriting.overlay_title) à côté du rendu.
Les frames de contrôle attendues : 0 s (hook pur, visage), 2.9 s (fin du hook),
3.1 s (overlay visible), un zoom frame-exact (ex. 8.62 s pour A01), dernière
seconde (fade_to_black).

## Colonnes minimales

Chaque ligne doit renseigner : pack, angle, segment, canvas, gates G0-G3,
P1 (preview validée), P2 (rendu CI), run GitHub Actions, décision.

## 2026-09-10 — Architecture MULTI-VIDÉOS livrée (1 codex = N vidéos = 1 run = 1 zip)

- Doctrine Warsmith appliquée au bras armé PUR : un seul codex décrit TOUTES
  les vidéos finales ; le rendu déclenche UN run (matrix, max 20) ; le
  bundle (zip, zéro concat) part vers F05 pour camouflage/nettoyage.
- F00-PUR : `--append` multi-vidéos (pur_sources.json cumulatif).
- F03 Preview : chargeur multi-packs (sélection multiple), `parsePurPackMulti`
  (style + texte GLOBAUX appliqués à toutes les entrées), sélecteur ◀▶.
- F04 : `extractPurEntryManifest` (1 runner = 1 vidéo), porte de style ouverte
  aux 4 styles PUR, overlay global prioritaire (miroir preview).
- Workflow `dev10_pur_render.yml` réécrit : prepare (fetch + G0 dry-run +
  matrix) → render (N runners) → aggregate strict (`tools/pur_aggregate.py`).
- F05 : mode `--batch` (N MP4 → mêmes traitements 1:1 + rapport consolidé).
- Vérifié : conversion multi 3 packs (90 s, 2571 frames), extraction A02
  (857 frames), agrégateur 3/3 OK + 2/3 refus, F05 batch H.264 confirmé.
- **Aucun run CI lancé** — GO opérateur requis (règle du 2026-09-09).

## 2026-09-11 — Runs matrix E2E : 2 échecs, 2 fixes, le rendu A01 passe

| Run | Résultat | Cause / fix |
|---|---|---|
| [34574052207](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34574052207) | ❌ failure | 404 `sia_elastic_heart.mp3` : la machinerie ranking (héritage dev8/dev9, réutilisée par la voie PUR multi-styles) jouait `music_timeline.json` alors que le mp3 est absent du codebase de rendu. Fix `a59351f` — `musicTimeline=null` pour la voie PUR uniquement (parité avec le preview P1 : pas de musique de fond). Modes ranking/reveal inchangés. |
| [34575463702](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34575463702) | ❌ failure | **Rendu A01 ✅** — `pur_A01_finale.mp4` (2,5 Mo) bien présent dans l'artefact `pur-clip-A01`. Mais agrégat ❌ : `pur_aggregate.py` cherchait `pur_pur_a01_finale.mp4` — le manifeste `dev10.pur.v1` porte un `source_id` déjà préfixé (`pur_A01`) et la recherche re-préfixait → doctrine stricte = refus de publier. Fix `ba979c2` : `normalize_angle()` avant `find_result()` + log `▸` de `convert_pur_pack.mjs` (source_id) + 7 tests de non-régression (`F00_INGEST/tests/test_pur_aggregate.py`). Doctrine « refus si incomplet » INTACTE. |

- Fix vérifié en local sur les données RÉELLES du run 34575463702 (artefact
  + manifeste) → `BUNDLE COMPLET : 1/1` ✅.
- Les MP4 des runs du 11/09 restent des **brouillons techniques** jusqu'au
  contrôle visuel du Warsmith (règle du 2026-09-09).
- Prochain run : post-fix `ba979c2`, sur GO explicite de l'opérateur —
  plan et périmètre dans `TRACKING/TODO_CONTINUATION.md`.

## 2026-09-11 (après-midi) — Restauration du fix, puis PREMIER E2E MATRIX VERT (avec réserve P2)

| Run | Résultat | Détail |
|---|---|---|
| [34603785939](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34603785939) | ❌ failure | **Incident de restauration** : le commit docs 6b30e38 avait reconstruit son arbre depuis l'arbre d'avant le fix ba979c2 (piège API REST : `base_tree` doit être l'arbre du HEAD courant, pas un vieil arbre) → l'ancien agrégateur est reparti (log `▸ undefined`, `pur_pur_a01_finale` introuvable). Rendu A01 ✅, aggregate ❌. Leçon enregistrée ; fix restauré par `b57a6a3` (blobs identiques, arbre courant). |
| [34605484040](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34605484040) | 🟢 jobs verts — **P2 NON VALIDÉ** | prepare ✅ render ✅ **aggregate ✅** — `▸ pur_A01` (log corrigé), `[✓] A01 : pur_A01_finale.mp4`, `BUNDLE COMPLET : 1/1`, artefact `lac-pur-final` publié. **MAIS** durée mesurée 14,357 s ≠ ~28,6 s attendues (857 frames @ 30 fps) → porte P2 « durée ≈ manifeste » **échouée**. Pas de tag canonique tant que P2 n'est pas levée. |

### Diagnostic P2 — fps de composition écrasé par un héritage dev7

- `F03_PICTOR/CODEBASE/src/Root.jsx` : `fps = sequences.fps || video.fps || 30`.
- `src/data/sequences.json` (héritage dev7, committé) porte `fps: 59.94006`, `total_frames: 0` →
  la composition PUR tourne à **59,94 fps** : 857 frames rendues mais 14,36 s de vidéo
  (2× trop rapide / moitié du segment). Le comptage « 857/857 frames ✓ » masquait le problème
  depuis le run du 09-09 : les frames sont là, c'est le TEMPS qui est comprimé.
- Manifeste PUR correct : fps 30, total_frames 857, 28,57 s — parité preview/rendu rompue par Root.jsx.
- **Piste de fix (à valider Warsmith)** : dans Root.jsx, voie PUR → fps depuis le manifeste PUR
  (ou : le workflow injecte aussi sequences.json fps=30 par run). Puis re-run A01, contrôle
  visuel, et seulement ensuite tag `pur-canon-v1`.

### Fix P2 — fps de composition imposé par le manifeste PUR (`727b131`)

- `F03_PICTOR/CODEBASE/src/Root.jsx` : la voie PUR utilise désormais
  `compositionFps = purManifest?.fps || fps` (le manifeste dev10.pur.v1, fps 30,
  est la source de vérité) ; les modes hybrid/reveal/ranking conservent la chaîne
  `sequences.fps` inchangée. Commit `727b131` construit sur l'arbre courant
  (leçon de l'incident `6b30e38` appliquée), syntaxe JSX vérifiée avant push.
- [34616549605](https://github.com/kioka8877-ux/LACRIMAE/actions/runs/34616549605) | 🟢 VERT — **P2 VALIDÉE** | prepare ✅ render ✅ aggregate ✅ ;
  `[✓] A01 : pur_A01_finale.mp4 (3.3 Mo, 28.629s)` — durée conforme au manifeste
  (857 frames @ 30 fps), `BUNDLE COMPLET : 1/1`, artefact `lac-pur-final` publié.
  Reste avant tag `pur-canon-v1` : contrôle visuel Warsmith (hook 0 s, zoom 8,62 s,
  fade final, texte, aucune accélération).

## 2026-09-11 (après-midi) — MOTEUR UNIQUE : la fin de la divergence preview/rendu

### Cause racine découverte des rendus non conformes au codex

`OmniComposition.jsx` (PICTOR) re-routait le rendu PUR vers le **moteur RANKING de dev9**
(`buildRankingFromPur` → `RankingCompilationComposition`) dès que le style était autorisé :
le composant PUR de PICTOR n'a **jamais tourné** en CI. Blur, zooms, overlay boxé, SFX —
tout ce qui avait été validé en preview était contourné (les « rendus d'ancienne branche »
constatés par le Warsmith). La copie `_purPackComposition.jsx` de PICTOR (zooms non
appliqués) n'était que la moitié du problème : elle était de toute façon morte.

### Décision Warsmith (11/09) : moteur unique

- PICTOR rend avec **le composant validé en preview** : `purPackComposition.jsx`
  (source de vérité `F03_PREVIEW/CODEBASE/src/preview/_purPackComposition.jsx`,
  identique hors 2 adaptations ci-dessous — vérifié par diff), + `bridgeClipper.js`
  et `antiDetection.js` copiés octet pour octet.
- Suppression du re-routage ranking (`buildRankingFromPur` éradiqué) et du doublon
  `_purPackComposition.jsx` — la dérive preview/rendu devient structurellement impossible.
- **Voix du clip ON** (`muted: false`) — le codex dit « voix claire » hook ; musique de
  fond : reste coupée (décision du jour : pas besoin).
- **Mapping provisoire boom→impact** — `boom.mp3` n'existe dans aucun codebase ; à
  remplacer quand le Warsmith fournit le fichier.
- **Portes assets anti-404** : `sfx_available` calculé par `convert_pur_pack.mjs`
  (existance réelle des fichiers, jamais déclarée à la main) ; SFX validés copiés de la
  preview par une étape dédiée du workflow ; **porte P-AUD** dans `pur_aggregate.py` :
  un MP4 sans piste audio est refusé comme un rendu manquant.

### Commits

- `4f1598ce` — feat(pur): MOTEUR UNIQUE (composant preview, portes assets, P-AUD, SFX copiés)
- `e1561f27` — docs(pur): PUR_GATES P-AUD + P-ENGIN ; README : mission réelle de F04 SIGNUM

### Prochaine étape

Run A01 post-moteur-unique (GO Warsmith requis, règle du 09-09) → contrôle visuel →
tag `pur-canon-v1`. Attendu cette fois : blur codex (24px, bande 46% à y 52%), zooms
1,15×/1,30× à 8,62 s et 24,43 s, SFX impact aux 2 zooms, voix du clip audible,
overlay boxé unique 44px à y 11%.

### Run 34724140887 (commit 108b688) — tous assets ✓ + diagnostic audio

- G2 deux passes : A03 re-decoupe localement (dérive +1,35 s corrigee) -> 3/3 jobs verts,
  agregation OK, bundle final publie.
- **Post-mortem operateur** : gel ~14 s (double avance `startFrom`, fix -> 0),
  gonflements (`breathing_zoom` cache des assets + saut du swell -> corriges via
  `fx_mode=off`), double voix (couches blur -> `mute_bg=true`).
- Interrupteurs pilotables depuis le workflow : `fx_mode` (asset|off), `mute_bg` (bool).

### Run isolation 34744097428 (commit d3e6ee4) — preuve des fixes (6 s, A01, fx_mode=off)

- SUCCES. Mesures ffprobe du final : video 6,033 s / audio 6,080 s — synchro A/V
  retablie (avant : A03 audio +1,3 s de derive, contenu epuise en ~14,3 s).
- startFrom=0 verifie : 6 s de timeline = 6 s de contenu reel, plus de course.
- mute_bg verifie : une seule piste vocale dans le mux.

### 2026-09-14 — HEISENBERG : sous-frégate Caviar opérationnelle (Groupe 2)

- **Nouvelle frégate embarquée dans F03_PICTOR** (`F03_PICTOR/HEISENBERG/`) :
  reçoit les vidéos FINIES (sortie F03, validées par le gate qui suit), les
  analyse via le Directeur Caviar (Groupe 1, zéro doublon) et émet un
  `caviar_manifest_<stem>.json` par vidéo finale — verdict OK/BLOCKED/REFUSED,
  Budget d'Attention (100 u, dépense ≤ 55 u), propositions advisory
  (jump cuts, smash audio, punchline whisper).
- **Budget d'Attention en fichier unique** (`caviar_budget.json`) : même
  source pour la frégate (refus à l'émission) et les gates P-CAV du bras
  armé (rouge au rendu si divergence) — double barrage voulu par le Warsmith.
- **B-roll NUMÉROTÉ** : PERTURABO ne voit jamais les fichiers. Il écrit
  l'émotion + « met le numéro 1 » ; Heisenberg résout le numéro, pose le
  flash blanc à l'ENTRÉE (jamais à la sortie) et le SFX couplé sur la même
  frame. Pas de vidéo dans BROLL/FILES/ = pas de B-roll proposé.
- **> 8 silences = REFUS** : « segment mauvais, prends un autre » — aucun
  manifeste toxique émis, diagnostic copié dans OUT/hold/.
- **CI** : étape advisory après l'agrégation dans `dev10_pur_render.yml`
  (échec non bloquant — la frégate conseille, la livraison passe).
- **Tests** : `test_heisenberg.py` 20/20 verts + `test_caviar.py` Groupe 1
  inchangé et vert (non-régression vérifiée).
- Doctrine rappelée : Heisenberg propose ; PERTURABO tranche le OÙ/QUOI ;
  Warsmith valide au gate. Prochain groupe (3) : le rendu narratif —
  B-roll numéroté au rendu, jump cuts, ducking.

## 2026-09-15 — GROUPE 3 : le rendu narratif est en place

- **Moteur de rendu** `F03_PICTOR/CODEBASE/src/caviarRender.js` : le bras armé
  exécute le bloc `caviar` du pack — jump cuts (tuiles source↔timeline sans trou),
  punch-ins (peak ≤ 1.15), B-roll numéroté (overlay plein cadre, voix continue,
  flash blanc à l'ENTRÉE + SFX sur la même frame), ducking au climax. Le bloc
  absent = rendu historique à l'identique (zéro régression).
- **Anti-saturation au rendu** : le moteur vérifie le Budget d'Attention avant
  d'appliquer — excédent déposé (le plus cher puis le plus tardif d'abord), la
  respiration gagne (source seule ≥ 60-70 % de la timeline), gate rouge.
- **Double barrage opérationnel** : frégate refuse à l'émission (H2/H3) +
  `caviar_gate.py` rouge dure en CI (pack avant rendu, agrégat avant publication,
  budget PAR entrée). Miroir `src/data/caviar_budget.json` diffé à chaque rendu.
- **Tests** : moteur 20/20 (`npm run test:caviar`), gate 14/14, frégate 20/20,
  Groupe 1 vert. fx_mode=off : « clip normal » conserve les jump cuts.
- Prochain groupe (4) : la mémoire ARCHIVUM — `ARCHIVUM/narrativum/` après
  décision doctrinale de conservation.

## 2026-09-15 (v2) — Pack v2 + partition F00D : réception adaptée et vérifiée

- Note technique PERTURABO reçue et confrontée au code : doctrine identique
  (budget 100/55u, flash/SFX entrée-seule, élément unique), seuls les noms de
  champs changent → adaptateur `caviarV2.js` + portes v2 du gate.
- **Pack réel voxc-2** (`production_pack_pur_voxc2_blur_v2.json`, branche
  v2-live-vox-c) validé en lecture seule : portes vertes, budget 32u
  recalculé == 32u déclaré (respiration 68u), BLUR-01/02 résolus via le
  registre sémantique, flashs aux bons frames à speed 1.05.
- Pièges traités : OUT/ gitignoré (canal EXPORT/), DRAFT non exécutable,
  détection par présence de blocs (vieilles clés jamais exigées), smash/
  panels au top de la partition OU sous events.* (les deux acceptés).
- CI : étape gate étendue (`--pack-v2` + checksum best-effort via le
  manifeste F00D déclaré). Tests : v2 12/12, gate 24/24, moteur 21/21.
- À venir : rendu du panneau possédé par la partition (crop_zoom/blur/panel)
  puis rendu réel de bout en bout — après GO opérateur.
