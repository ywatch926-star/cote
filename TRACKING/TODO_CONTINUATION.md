# LACRIMAE dev10 — TODO DE CONTINUATION

> Point d'entrée obligatoire après toute migration de sandbox.
> Dernière mise à jour : 2026-09-14.

## État confirmé

Le dépôt est `https://github.com/kioka8877-ux/LACRIMAE`, branche `dev10`
(commit de référence `ba979c2` — 2026-09-11, fix agrégateur). dev10 est canonisé **bras armé du mode PUR**
de PERTURABO (`kioka8877-ux/PERTURABO`, `MONDES_FORGES/CLIPPING`) : le pack
PUR entre, le MP4 final sort, 100 % GitHub Actions.

Travail PUR réalisé sur la branche de travail `dev10-pur` (commits
`42a9ebc`, `61b719f` + lot 3) : BridgeClipper v2, F00-PUR ingest, onglet
PUR F03, rendu F04 parité, workflow `dev10_pur_render.yml`, bridge `--pur`,
docs (PUR_GATES / PUR_CAMPAIGN_LOG / PUR_IMPLEMENTATION / guide opérateur).

## Priorités canoniques

1. **Mode PUR — bras armé PERTURABO** (unique mission de dev10) :
   `F00-PUR → bridge --pur → F03 Preview ⚡ PUR → dev10_pur_render.yml`
2. **HEISENBERG (sous-frégate Caviar, 2026-09-14)** : implémentée et
   opérationnelle dans `F03_PICTOR/HEISENBERG/` — voir
   `TRACKING/HEISENBERG_PLAN.md` + `TRACKING/HEISENBERG_GATES.md`.
   Émet un `caviar_manifest_<stem>.json` par vidéo finale ; étape CI
   advisory branchée après l'agrégation. Phases restantes : Groupe 3
   (rendu narratif du pack — B-roll numéroté au rendu, jump cuts,
   ducking) puis Groupe 4 (conservation ARCHIVUM/narrativum).
3. **F00H (hook 2 s)** : implémenté, test réel REPORTÉ — non prioritaire.
   Reprendre via `TRACKING/F00H_GATES.md` quand décidé.
4. **Test réel Ranking dev9** : hérité de dev9, non exécuté. Non bloquant
   pour PUR — ne pas mélanger les assets.

## Prochaine étape exacte (PUR)

Le preview dispose des **panneaux de configuration opérateur** (texte
overlay, style blur/split/reframing, anti-détection) — voir
`TRACKING/GUIDE_BRAS_ARME_PUR.md` étape 3. État :

1. ✅ Clip pur_A01 réparé (la copie .mp4 était tronquée — moov atom absent)
2. ✅ Panneaux F03 branchés sur `style_params` (dev10.pur.v1) + rendu par
   style (blur dual-layer / split top-bas / reframing) + miroir F04 synchronisé
3. ✅ **Texte overlay v2 IMPLÉMENTÉ (2026-09-10)** — phases A-E de
   `TRACKING/PUR_TEXT_IMPLEMENTATION.md` : texte statique début→fin, auto-fit
   (1 ligne = 1 ligne visuelle, max 3, min 28 px), boîte coins arrondis +
   padding, preset « Référence TikTok » (boîte blanche, texte noir,
   Montserrat, casse mixte), curseur position verticale de la vidéo nette
   (blur). Boutons +/− lignes dans le panneau. Miroir F04 synchronisé.
4. ✅ **Codex de base PUR propre (2026-09-10)** : `public/codex.json`
   régénéré (racine pur_pack, manifeste = réglages opérateur validés,
   archive Spider-Man dans clips[0]) + exportCodex corrigé (review_mode
   racine synchronisé, pur_manifest racine rempli) + Montserrat ExtraBold
   embarquée F03/F04 (parité police preview/CI).
5. ✅ **Architecture MULTI-VIDÉOS IMPLÉMENTÉE (2026-09-10)** — voir
   `TRACKING/PUR_MULTI_VIDEOS.md` : 1 codex = N vidéos = 1 run = 1 zip.
   Chargeur multi-packs F03 (sélection multiple), `parsePurPackMulti`
   (style + texte GLOBAUX appliqués à toutes les vidéos), sélecteur ◀▶
   « VIDÉO X/N », workflow matrix (prepare → N renders parallèles 1-20 →
   aggregate strict), `tools/pur_aggregate.py` (refus de publier si un MP4
   manque), `convert_pur_pack.mjs --packs`, F05 `--batch`.
6. ✅ **Fix agrégateur (2026-09-11, commit `ba979c2`)** — le rendu matrix
   A01 réussissait (run 34575463702) mais l'agrégat refusait le bundle :
   identifiants d'entrée déjà préfixés (`pur_A01`) re-préfixés →
   `pur_pur_a01_finale.mp4` introuvable. `normalize_angle()` + 7 tests
   (`F00_INGEST/tests/test_pur_aggregate.py`). Doctrine de refus INTACTE.
   Récit complet des 2 runs du 11/09 : `TRACKING/PUR_CAMPAIGN_LOG.md`.
7. **Validation visuelle P1** par le Warsmith sur le preview — GO obligatoire
   avant tout run CI (règle du 2026-09-09)
8. ✅ E2E PUR réel post-fix RÉALISÉ (11/09) : run 34605484040 (jobs verts
   mais P2 échouée : fps écrasé par sequences.json hérité dev7 → 14,36 s),
   puis run 34616549605 après fix fps (`727b131` — Root.jsx voie PUR lit le
   fps du manifeste dev10.pur.v1) → **28,629 s mesurées, BUNDLE COMPLET
   1/1, P2 techniquement validée**. Récit : PUR_CAMPAIGN_LOG.md.
9. **Contrôle visuel du MP4 A01 (28,6 s)** par le Warsmith — artefact
   `lac-pur-final` du run 34616549605 : hook à 0 s, zoom 8,62 s, fade final,
   texte lisible, aucune accélération perceptible.
10. Tag canonique à la validation : pur-canon-v1

## Contrats à préserver

- Pack PUR : `production_pack_pur_*.json` — propriété PERTURABO F06_DIRECTOR.
  JAMAIS modifié côté dev10 ; corrections à remonter au monde forge.
- Manifeste : `dev10.pur.v1` produit par `parsePurPack()` (bridgeClipper.js).
- Parité preview/render : `_purPackComposition.jsx` identique en F03 et F04.
- Anti-détection obligatoire (mirror + speed + zoom) — doctrine
  `_PIEGES_APPRIS_PUR.md` de PERTURABO.

## Règles de reprise

Vérifier `git status --short --branch`, lire ce fichier et
`TRACKING/PUR_IMPLEMENTATION.md`. Chaque gate journalisé avec son commit /
run CI / artifact. Ne pas lancer F04 avant validation visuelle F03.
Les assets volumineux (clips téléchargés) ne sont JAMAIS commités : ils
transitent par les artefacts CI ou les Releases GitHub (SHA-256 si besoin).

## Migration sandbox

```bash
git clone https://github.com/kioka8877-ux/LACRIMAE.git
cd LACRIMAE
git fetch origin --prune
git checkout dev10            # ou dev10-pur pour le travail PUR
cat TRACKING/TODO_CONTINUATION.md
```

## Mise à jour 2026-09-11 (après-midi) — moteur unique posé

- ✅ Cause racine identifiée : re-routage ranking (`buildRankingFromPur`) qui masquait
  le moteur PUR en CI — supprimé (commit `4f1598ce`).
- ✅ PICTOR rend désormais avec le composant preview validé (voix ON, mapping boom→impact
  provisoire, portes assets `sfx_available` + P-AUD).
- ⏭ Prochaine étape : run A01 post-moteur-unique (GO Warsmith) → contrôle visuel
  (blur/zooms/SFX/voix) → tag `pur-canon-v1`.
- ⏭ En attente du Warsmith : fichier `boom.mp3` (pour lever le mapping provisoire) ;
  purge éventuelle du codex preview (héritages dev4/dev9).

---

## 2026-09-12 — Run vert jfbjfojfonf + swell continu + flash blanc

- **Fix staticFile() validé en CI** : run [34686817585](https://github.com/jfbjfojfonf/LACRIMAE/actions/runs/34686817585)
  100 % VERT (prepare → render → agrégation stricte 1/1). Sortie : `pur_A01_finale.mp4`
  19,3 Mo / 28,6 s, voix ON, SFX impact/boom, miroir + crop anti-détection.
  Artifact `lac-pur-final` prêt pour F05 CAMOUFLAGE.
- **Décisions Warsmith 2026-09-12 (implémentées aujourd'hui)** :
  - **Swell continu** remplace le zoom à retour instantané : montée douce → tenue →
    redescente douce vers 1.0, une seule courbe (`purZoomAtFrame` + ease in-out,
    champs asset `hold_frames` / `release_frames`).
  - **Flash blanc** de transition 5 frames (montée/descente symétriques),
    déclenché par `entry.zooms[].white_flash === true`.
  - **Garde-fou speed** : G0 signale tout asset dont `speed > 1.03`
    (accélération perceptible — PERTURABO doit passer à 1.01-1.02).
  - **Vocabulaire corrigé** : asset = A01/A02/… (1 vidéo finale = 1 job runner),
    pack = l'ensemble des assets. Workflow et docs renommés en conséquence.
- **Note PERTURABO** : `TRACKING/PERTURABO_NOTE_2026-09-12.md`
  (speed, schéma swell, flash blanc, renommage `asset_pur_*`).
- **À faire ensuite** : run de validation avec TOUS les assets (A01+A02+A03,
  filtre vide, 3 jobs parallèles), puis chantier panneaux de configuration
  (texte/couleurs/contours/position, blur/split/reframing).

---

## 2026-09-12 (soir) — Run tous assets 34721632577 : A01 ✓ A02 ✓ A03 ✗ → fix G2

- **Run 34721632577** (commit `df23f0a`, 3 jobs parallèles) : A01 ✓ (28.6s), A02 ✓ (28.6s),
  A03 ✗ — **G2 DUREE 31.35s ≠ 30.0s ±0.5**. Cause : dérive de fragments HLS Twitch
  (~+1-2 s) malgré `--force-keyframes-at-cuts` (déjà actif dans la commande).
  Agrégation : refus propre de publier le bundle (règle dev9 respectée, 1 rendu manquant).
- **Fix appliqué (f00_pur.py)** : G2 à deux passes — si excès ≤ +3 s, re-découpe locale
  ffmpeg (re-encode libx264 crf18, `-t durée_attendue`, purge auto du fichier périmé)
  puis re-probe ; échec G2 seulement en dernier recours.
- **Speed 1.05 MAINTENU par décision de l'opérateur** (le garde-fou G0 signale >1.03
  mais n'applique aucune correction moteur).
- **À faire ensuite** : relance run tous assets (planifié ci-dessous), puis chantier
  panneaux de configuration preview.

---

## 2026-09-12 (nuit) — Diagnostic audio/video run 34724140887 : DOUBLE startFrom + template cachee + fix

- **Run 34724140887 (tous assets) : SUCCES complet** — G2 deux passes a sauve A03,
  agrégation stricte satisfaite, bundle `lac-pur-final` publié (3 MP4).
- **Constat operateur** : audio « qui court » (compression + course), video gelee
  vers ~14 s sur A03, gonflements bizarres.
- **Cause racine (prouvee)** : `startFrom: Math.round(localFrame * speed)` dans
  `purPackComposition.jsx` DOUBLAIT l'avance du clip (seek + progression Remotion ~ 2,1x)
  -> 30 s de contenu epuisees en ~14,6 s de timeline ; la voix se retrouve comprimee dans ce
  temps reduit. Le speed 1.05 n'ajoutait que 5 % : ce n'etait PAS lui.
- **Template cachee des assets** : `breathing_zoom` (1.02 <-> 1.08, cycle 8 s) enfouie
  dans l'anti_detection des packs -> gonflement perpetuel. Et bug de mon swell :
  retour a 1.0 au lieu de `scale_from` -> saut visible de -8 % apres chaque zoom.
- **Double audio (style blur)** : les 2 couches Video (floue + nette) portaient toutes
  deux la voix -> echo/course.
- **Fixes (interrupteurs, aucun asset modifie)** :
  - `startFrom: 0` (fix de bug, toujours actif) — Remotion avance SEUL depuis 0.
  - `fx_mode=off` (input workflow) : AUCUN zoom/swell/breathing — clip normal.
    Miroir + crop + speed conserves (decision operateur).
  - `mute_bg=true` (input workflow, defaut) : couche arriere blur muette, une seule voix.
  - Flash blanc de transition : TOUJOURS actif (hors fx_mode, non concerne).
- **Protocole d'isolation 6 s** : mini-rendus `max_duration=6` par combinaison
  d'interrupteurs avant le run complet — comparaison rapide, pipeline intact.
- **A faire ensuite** : mini-rendu 6 s (A01, fx off) -> controle visuel operateur ->
  run complet tous assets avec fx_mode=off.
- **Mini-rendu 6 s EFFECTUE (run 34744097428, SUCCES)** : A/V synchro prouvee
  (video 6,03 s / audio 6,08 s). Fixes valides -> run complet tous assets lance
  avec fx_mode=off + mute_bg=true.

---

## 2026-09-13 — Brainstorm Caviar 99 % + SPEC PERTURABO redigee (aucune implémentation)

- Run complet 34744374215 (tous assets, fx_mode=off, mute_bg) : SUCCES total cote
  pipeline — clips propres, sans montage narratif (etat des lieux actuel).
- Brainstorm « Caviar 99 % » (7 cuts, 4 piliers, analogie Heisenberg) avec l'operateur :
  doctrine des roles (PERTURABO = le OU/QUOI, LACRIMAE = le COMMENT, Warsmith tranche),
  flash blanc = entree de B-roll UNIQUEMENT (sortie en Flow Cut), budgets anti-saturation
  en portes bloquantes (pas des warnings).
- **Note de cadrage ecrite : `TRACKING/CAVIAR_SPEC_PERTURABO.md`** — schema JSON cible
  (narrative / broll / audio_design, retrocompatible v2), grammaire des 7 cuts avec
  faisabilite, doctrine, ce que PERTURABO doit ajouter aux packs, ce que LACRIMAE
  construira (Directeur : silences, amplitudes, whisper CPU, gates P-CAV), phases 0-4.
- **Rien n'est implemente** : GO operateur requis a chaque phase (regle du 09-09).
  Prochaine etape : PERTURABO valide/amende le schema §5 + fournit un pack de test.

---

## 2026-09-13 (suite) — GO operateur : GROUPE 1 CAVIAR implemente (Directeur + Porte P-CAV)

- **`F00_INGEST/CODEBASE/caviar.py`** (nouveau module) :
  - `gate_pcav_budgets()` : porte P-CAV BLOQUANTE — schema narratif (hook_type,
    is_climax, energy_curve) + budgets anti-saturation (broll<=3 et <=45 frames,
    sfx obligatoire, flashs<=3 espaces >=1,5s, zooms<=4 espaces >=2s, element unique,
    broll interdit pendant la resolution). Champs absents = bypass (packs v1).
  - `analyze_clip()` : LE DIRECTEUR (advisory, jamais bloquant) — carte des silences
    (ffmpeg silencedetect), clusters RMS (candidats is_climax), whisper CPU optionnel
    (punchline = dernier mot avant la plus longue pause).
- **Cablage f00_pur.py** : P-CAV s'execute apres G0 (echec = job rouge) ; le Directeur
  tourne apres G3 et ecrit `pur_caviar_<angle>.json` + resume dans pur_sources.json
  (cle `caviar`). Echec d'analyse = tolere et journalise.
- **Tests** : `F00_INGEST/tests/test_caviar.py` — 20/20 verts (budgets, schema, clusters
  RMS, detection silence ffmpeg). Tests existants f00_pur : 9/10 verts — le fail
  `test_find_downloaded_file_prefers_mp4` est PRE-EXISTANT (identique sans mes mods).
- **Doc** : `TRACKING/CAVIAR_GATES.md` (regles P-CAV + Directeur + phases restantes).
- **Prochaine etape** : Groupe 2 (Phase 3 rendu narratif) APRES pack de test PERTURABO
  + GO operateur : Jump Cuts (table source<->timeline + recalcul durees G2/aggregate),
  ducking is_climax, rupture overlay, rendu B-roll.

---

## 2026-09-15 — GO operateur : GROUPE 3 CAVIAR implemente (rendu narratif + double barrage)

- **`F03_PICTOR/CODEBASE/src/caviarRender.js`** (nouveau moteur, fonctions pures) :
  - `buildCaviarTimeline()` : jump cuts = tuiles contigues timeline<->source (aucun
    trou, aucun debordement) ; chaque tuile lit `startFrom` source ; evenement tombant
    DANS un silence retire recale au point de coupe ; mapping `sourceToTimelineFrame()`.
  - Punch-ins : courbe attack/hold/release, peak plafonne 1.15, jamais de zoom libre.
  - B-roll numerote : overlay plein cadre (voix du clip CONTINUE), flash blanc a
    l'ENTREE uniquement + SFX couple meme frame ; PAS de fichier resolu = PAS de B-roll.
  - Smash audio : `caviarDuckVolumeAtFrame()` (-12 dB, rampe 2 frames) — s'activera
    quand une piste musicale PUR existera.
  - fx_mode=off (« clip normal ») : punch-ins/flashs/B-rolls deposes, jump cuts
    CONSERVES (coupes de montage, pas des effets).
  - **Double barrage rendu** : `verifyCaviarBudget()` + `enforceCaviarBudget()` —
    depense > 55u ou cap depasse → evenements DEPOSES (le plus cher puis le plus
    tardif d'abord) + gate rouge rapporte. Bloc `caviar` absent = rendu historique
    a l'identique (zero regression).
- **Wiring `PurPackComposition.jsx`** : segments jump cuts → `videoProps.startFrom`,
  punch-ins multiplies dans le transform, B-roll/flash/SFX rendus, parite preview/CI.
- **`F03_PICTOR/HEISENBERG/caviar_gate.py`** (nouveau gate, ROUGE DURE) : verifie le
  bloc caviar du pack (depense, caps PAR entree, flash entree-seule, SFX entree-seule,
  B-roll sans fichier, element unique) — avant rendu ET sur le manifeste agrege avant
  publication du bundle final.
- **Miroir budget** : `src/data/caviar_budget.json` (copie exacte de la source
  HEISENBERG) — diff verifie a chaque rendu CI (H-MIRROR).
- **CI `dev10_pur_render.yml`** : etapes H-MIRROR + H-ENGINE (`npm run test:caviar`)
  + H-PACK (gate par runner) + H-AGGREGATE (gate sur l'agregat) — bloquantes.
- **Tests** : `tests/caviar_render.test.mjs` 20/20 verts (zero dependance externe,
  runner minimal `tests/harness.mjs`) + `test_caviar_gate.py` 14/14 verts +
  non-regression `test_heisenberg.py` 20/20 + `test_caviar.py` Groupe 1 vert.
  Un vrai bug attrape par les tests : le check de chevauchement des jump cuts
  comparait `cut_at_sec` au lieu du DEBUT du silence (corrige).
- **Prochaine etape** : Groupe 4 — memoire ARCHIVUM (`ARCHIVUM/narrativum/` :
  manifest_ledger, gate_history, retention_log A/B caviar vs basique, lessons)
  APRES decision doctrinale de conservation ; puis pack de test PERTURABO avec
  bloc `caviar` pour un rendu reel de bout en bout.
