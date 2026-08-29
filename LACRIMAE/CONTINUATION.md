# LACRIMAE — CONTINUATION INTER-SANDBOX

**Dernière mise à jour : 28 août 2026**

## Règle de reprise

Lire ce fichier en premier, puis `SANDBOX_ARCHIVE_MANIFEST.md`, `README.md`, `docs/V2_OPERATIONS_GUIDE.md` et `V2_EVOLUTION_ROADMAP.md`. Ne jamais modifier `dev6` pour les essais expérimentaux : travailler uniquement sur `dev6-B`.

## État Git exact

| Branche | Commit distant | Rôle |
|---|---|---|
| `dev6` | `4c0a7a9` | Version stable validée, à préserver |
| `dev6-B` | `4b24ee5` | Branche active, héritage v2 |

Derniers commits importants de `dev6-B` (héritage v2) :

- `3b78ee2` — feuille de route v2.
- `b905fe5` — AUSPEX adaptatif et contrôles Motus Viral.
- `29811b5` — stride de restauration faciale sur frames interpolées.

Dépôt : `https://github.com/kioka8877-ux/LACRIMAE`.

## Ce qui existe dans chaque branche

### dev6 stable

`dev6` contient la Frégate DOMINUS HYPERFLUIDA fonctionnelle : Oracle universel, RIFE 4.25, restauration GFPGAN v1.3, restauration native, texture, finition Lumen, CHROMA DOMINATUS, conservation du format et conservation audio lorsqu’un flux audio existe.

Le parcours validé est : `F00 → F01 → F02 → F03 → F04 → F05 → F06 → F07 → F08 → F10`.

### dev6-B active (héritage v2)

`dev6-B` ajoute :

- `ORACLE/auspex.py` avec AUSPEX PIXEL/TEMPORAL, exécutable localement avec FFmpeg/Pillow sans OpenCV obligatoire.
- Mode Oracle `auto`, qui analyse la source avant le calcul GPU et recommande un profil.
- Profils `hdr_imperator`, `realistic_aurea`, `old_main_noctis` et `viral_imperator` dans `CONFIG/atom_ic_profiles.json`.
- F08 avec paramètres Motus optionnels : frame blending et motion blur, par défaut désactivés ou transparents.
- Stride facial configurable pour éviter de traiter toutes les frames interpolées avec GFPGAN.
- Documentation dev6-B : README, guide opérationnel, contrat DOMINUS, panneau de contrôle, TODO, gates et ledger de campagnes.

## Dernier test Modal réussi

Le dernier compte opérationnel est l’espace Modal **`tekfugo`**, chargé par le fichier local `.env.modal`. Les secrets ne sont pas dans GitHub.

Application déployée : `lacrimae-dev6-video`.

Volumes :

- `lacrimae-dev6-video` — vidéos et campagnes.
- `lacrimae-dev6-models` — poids RIFE et GFPGAN.

Déploiement : `https://modal.com/apps/tekfugo/main/deployed/lacrimae-dev6-video`.

Campagne finale réussie : `v2_original_5s_run2`, depuis la source originale `rife_input_5s.mp4`.

Résultat :

- Source : 1920×1080, 30 FPS, 150 frames, 5,000 secondes.
- Sortie : 1920×1080, 120 FPS, 597 frames, 4,975 secondes.
- Profil AUSPEX : `hdr_imperator`.
- F05 : GFPGAN v1.3, 272 détections, `frame_stride=4`, environ 121 secondes.
- F08 : `temporal_strength=0.0`, actuellement garde temporelle transparente.
- Source sans audio ; la sortie ne peut donc pas contenir d’audio.
- Statut Oracle : `SEALED`.

Sortie locale : `.test/v2_production_tekfugo_final/campaigns/v2_original_5s_run2/F10_CUSTOS_RESTITUTIO/v2_original_5s_run2_final.mp4`.

## Blocages et corrections connus

Un ancien compte Modal avait atteint sa limite de dépense. Le nouveau fichier `.env.modal` pointe vers `tekfugo`, qui a d’abord été vide. Il a fallu déployer l’image puis remplir manuellement `lacrimae-dev6-models` avec RIFE 4.25 et GFPGAN v1.3. Les poids locaux sont dans `.model_downloads/`, ignorés par Git.

L’erreur F05 initiale venait du traitement GFPGAN sur 597 frames. Le correctif `29811b5` a ajouté un stride facial configurable. L’erreur RIFE du nouvel espace venait de poids absents du Volume, pas du code.

## Travail en cours

Le prochain chantier est la création d’une sous-frégate de presets de compositing, prévue sous le nom **F09 AETHER COMPOSITUM**. L’objectif est de reproduire la logique du preset After Effects `cc2.ffx` : netteté, Unsharp Mask, Magic Bullet Looks, gradient/overlay et compositing multicouche.

Le fichier reçu `cc2.ffx` est conservé localement sous `.test_cc2.ffx` et analysé dans `CC2_FFX_ANALYSIS.md`. Il est binaire After Effects et ne doit pas être poussé au dépôt comme s’il s’agissait d’une LUT. Il révèle les effets suivants : `ADBE Sharpen`, `ADBE Unsharp Mask2`, `MB LookSuite3 / Magic Bullet Looks` et `S_Gradient`.

Presets headless prévus : `silver_gray`, `dark`, `warm`, `viral_hdr` et `clean_realistic`. Ils devront être des configurations versionnées, avec couches activables, opacités contrôlées, protection des noirs et limitation des halos.

## Priorité technique suivante

1. Ne pas lancer de GPU avant d’avoir défini F09 et ses paramètres.
2. Créer la spécification des presets multicouches à partir de `cc2.ffx`.
3. Mapper chaque effet After Effects vers FFmpeg/Python : `unsharp`, courbes, levels, extraction highlights, blur, screen/softlight/overlay, gradient, glow, grain et recomposition.
4. Ajouter une sélection Oracle de preset séparée du profil Enhance.
5. Tester localement les couches sur les rendus déjà téléchargés.
6. Lorsqu’un nouveau compte GPU est disponible, lancer un seul test de 5 secondes avec plusieurs presets comparables.

## Fichiers importants

| Fichier | Rôle |
|---|---|
| `ORACLE/universal_run.py` | Orchestrateur principal |
| `ORACLE/oracle.py` | Validateur et registre de campagnes |
| `ORACLE/auspex.py` | Analyse locale adaptative |
| `modal/workers/video_worker.py` | Worker GPU Modal |
| `CONFIG/atom_ic_profiles.json` | Profils de traitement |
| `CC2_FFX_ANALYSIS.md` | Analyse du preset After Effects reçu |
| `README.md` | Documentation principale dev6-B (héritage v2) |
| `docs/V2_OPERATIONS_GUIDE.md` | Procédure opérationnelle |
| `docs/DOMINUS_HYPERFLUIDA_V2_CONTRACT.md` | Contrat technique |
| `docs/V2_CONTROL_PANEL.md` | Panneau de contrôle documentaire |
| `V2_EVOLUTION_ROADMAP.md` | Feuille de route expérimentale |
| `SANDBOX_ARCHIVE_MANIFEST.md` | Règles d’archivage et reprise |

## Sécurité

Ne jamais committer `.env.modal`, `.env.modal.*` réel, tokens, clés Backblaze, fichiers `.ffx` privés ou gros modèles. Les règles `.gitignore` les excluent. Les vidéos et sorties locales sont dans `.test/` et doivent être transférées séparément ou régénérées depuis les Volumes.

## Commande de reprise conceptuelle

```bash
cd /home/ubuntu/LACRIMAE_DEV6
git checkout dev6-B
git pull --ff-only origin dev6-B
python3 -m py_compile ORACLE/*.py modal/workers/video_worker.py
python3 -m json.tool CONFIG/atom_ic_profiles.json >/dev/null
python3 ORACLE/auspex.py --help
```

La prochaine session doit confirmer le contenu du compte Modal utilisé avant tout run et ne doit jamais supposer que les Volumes d’un nouveau workspace contiennent les modèles.
