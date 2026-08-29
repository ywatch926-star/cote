# Manifeste de sauvegarde et reprise sandbox

## Principe

GitHub est la source de vérité pour le code, les configurations et la documentation. Il ne doit pas devenir le stockage des secrets, des modèles lourds ou des vidéos de test.

## Déjà sauvegardé sur GitHub

Les éléments versionnés sur les branches `dev6` et `dev6-B` comprennent le code Oracle, le worker Modal, les configurations ATOM-IC, les contrats de Frégate, les tests, les guides, les rapports stratégiques et la feuille de route v2.

Branches distantes :

- `dev6` → `4c0a7a9`.
- `dev6-B` → `4b24ee5`, branche active issue de v2.

## À ajouter au commit de continuité

- `CONTINUATION.md`.
- `SANDBOX_ARCHIVE_MANIFEST.md`.
- `TRACKING/TODO_CONTINUATION.md`.
- `TRACKING/DEV6B_GATES.md`.
- `TRACKING/dev6b_campaign_ledger.json`.
- `TRACKING/DEV6B_CAMPAIGN_LOG.md`.
- `TRACKING/DEV6B_TRANSFER_LOG.md`.
- `CC2_FFX_ANALYSIS.md`.
- Les rapports d’analyse Topaz et fluidité déjà présents à la racine si leur taille reste raisonnable.
- Les documents de recherche utiles, sans fichiers secrets.

## À ne jamais pousser sur GitHub

| Catégorie | Emplacement typique | Action |
|---|---|---|
| Credentials Modal | `.env.modal`, `.env.modal.*` réel | Conserver hors dépôt, recréer manuellement dans le prochain sandbox |
| Credentials stockage | fichiers `storage.env`, tokens Backblaze | Conserver hors dépôt |
| Modèles | `.model_downloads/` | Transférer dans le Volume modèle ou retélécharger |
| Vidéos de test | `.test/`, fichiers MP4 lourds | Archiver séparément ou régénérer |
| Caches | `__pycache__/`, logs | Ne pas transférer sauf besoin de diagnostic |
| Presets privés | `.ffx` reçus sous accord privé | Conserver localement ; pousser seulement une analyse textuelle autorisée |

## Volumes Modal du dernier compte

Espace : `tekfugo`.

Application : `lacrimae-dev6-video`.

Volumes : `lacrimae-dev6-video` pour les campagnes et `lacrimae-dev6-models` pour RIFE/GFPGAN.

L’arborescence modèle attendue est :

```text
/models/models/RIFE/4.25/train_log/flownet.pkl
/models/models/RIFE/4.25/train_log/IFNet_HDv3.py
/models/models/RIFE/4.25/train_log/RIFE_HDv3.py
/models/models/RIFE/4.25/train_log/refine.py
/models/models/GFPGAN/1.3/GFPGANv1.3.pth
```

## Archive locale recommandée

Avant extinction du sandbox, créer une archive des documents et rapports, sans secrets, modèles ni vidéos :

```bash
mkdir -p /tmp/lacrimae_handoff
cp CONTINUATION.md SANDBOX_ARCHIVE_MANIFEST.md README.md V2_EVOLUTION_ROADMAP.md /tmp/lacrimae_handoff/
cp TRACKING/TODO_CONTINUATION.md TRACKING/DEV6B_GATES.md TRACKING/dev6b_campaign_ledger.json TRACKING/DEV6B_CAMPAIGN_LOG.md TRACKING/DEV6B_TRANSFER_LOG.md /tmp/lacrimae_handoff/
cp CC2_FFX_ANALYSIS.md ANALYSE_TROIS_REFERENCES_TOPAZ.md ANALYSE_FLUIDITE_VIRALE_ET_CIBLE_V2.md /tmp/lacrimae_handoff/
cp -r docs ORACLE CONFIG BACKUP /tmp/lacrimae_handoff/
tar -czf /tmp/LACRIMAE_dev6B_handoff_docs.tar.gz -C /tmp lacrimae_handoff
sha256sum /tmp/LACRIMAE_dev6B_handoff_docs.tar.gz
```

L’archive ne remplace pas GitHub : elle conserve les rapports locaux et les copies de documentation. Le code doit être récupéré avec `git clone` ou `gh repo clone`, puis la branche `dev6-B` doit être sélectionnée.

## Reprise dans le prochain sandbox

```bash
gh repo clone kioka8877-ux/LACRIMAE /home/ubuntu/LACRIMAE_DEV6
cd /home/ubuntu/LACRIMAE_DEV6
git checkout dev6-B
git pull --ff-only origin dev6-B
```

Ensuite, recréer localement `.env.modal` à partir des credentials du compte actif, sans l’ajouter à Git. Vérifier `modal profile list`, `modal volume list` et `modal app list`. Un nouveau workspace peut avoir les mêmes noms de Volumes mais des contenus différents.

## État de reprise

Le travail actif est la conception de **F09 AETHER COMPOSITUM**, une sous-frégate de presets multicouches inspirée du preset After Effects `cc2.ffx`. Les profils visés sont `silver_gray`, `dark`, `warm`, `viral_hdr` et `clean_realistic`.

La priorité n’est pas un nouveau rendu GPU immédiat. Il faut d’abord reproduire localement les couches Sharpen, Unsharp Mask, Magic Bullet Looks, gradient/overlay, glow, grain et compositing avec des équivalents headless, puis tester ces couches sur les sorties déjà disponibles.
