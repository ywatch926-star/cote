# LACRIMAE dev6 — Video Fleet MVP

`dev6` est la base de la flotte vidéo pilotée par l’Oracle du sandbox. La branche conserve l’historique de `dev4` et ajoute une architecture indépendante pour transformer une source HD en master 4K/120 FPS.

## État actuel

La fondation est installée : contrats de campagne, registre de workers, Oracle relançable, validateur `LAC_CUSTOS_VIDEO`, F00 d’inspection vidéo dev6, image GPU déclarative et workflow de test GitHub Actions.

Le mode simulation permet de traverser les dix frégates sans GPU et de vérifier les règles de transit. Le rendu IA réel n’est volontairement pas activé tant que les poids, le stockage objet et les identifiants du worker ne sont pas configurés.

## Commandes de fondation

```bash
python3 ORACLE/oracle.py create \
  --root ./.campaign_storage \
  --campaign-id demo_001 \
  --source /chemin/source.mp4 \
  --target-fps 120 \
  --profile quality_ultimate

python3 ORACLE/oracle.py simulate \
  --root ./.campaign_storage \
  --campaign-id demo_001

python3 LAC_CUSTOS_VIDEO.py \
  --root ./.campaign_storage \
  --campaign-id demo_001 \
  --stage F00_INGEST

python3 tests/test_foundations.py
```

## Flotte cible

| Frégate | Mission | Exécution prévue |
|---|---|---|
| F00 INGEST | Inspection, hash, FPS, rotation et manifeste | GitHub Actions / sandbox |
| F01 ANALYSIS | Plans, doublons, flashes et risques | GitHub Actions puis GPU si nécessaire |
| F02 MOTUS | Interpolation vers 60/120 FPS | Modal GPU |
| F03 RESTAURA | Restauration sélective | Modal GPU |
| F04 UPSCALE | Upscale vers 4K | Modal GPU |
| F05 LUMEN | Netteté et finition couleur | GPU ou CPU |
| F06 AUDIO | Conservation et synchronisation | GitHub Actions |
| F07 CUSTOS VIDEO | Contrôle technique et rapport | GitHub Actions |
| F08 CAMOUFLAGE | Encodage de livraison | GitHub Actions |
| F09 LUTHER | Nettoyage et scellement | GitHub Actions |

## Règle d’exécution

L’Oracle reste dans le sandbox. Il appelle les workflows légers et les fonctions Modal, attend leurs rapports, exécute les validations et ne déclenche jamais la frégate suivante avant un transit validé. Le registre `ORACLE/worker_registry.json` permet de remplacer un worker GPU sans changer les contrats.

Les vidéos doivent être placées dans un stockage indépendant. Les poids des modèles doivent être conservés dans un Volume persistant du worker GPU. L’image Modal contient l’environnement logiciel et est versionnée séparément des poids.

## Test réel

Le test en conditions réelles commencera par une courte séquence de 5 à 10 secondes. Il faudra fournir une vidéo source autorisée, configurer le stockage objet, préparer les poids des modèles et choisir le worker Modal actif. Le test sera ensuite chronométré et contrôlé avant d’être étendu à 30 secondes.

## Backend Backblaze B2

Le backend S3-compatible est disponible dans `SHARED/s3_storage_adapter.py`. Il est configuré uniquement par variables d’environnement ; les clés ne doivent jamais être ajoutées au dépôt.

```bash
export STORAGE_BACKEND=s3
export STORAGE_S3_ENDPOINT=https://s3.us-east-005.backblazeb2.com
export STORAGE_S3_REGION=us-east-005
export STORAGE_S3_BUCKET='NOM_EXACT_DU_BUCKET'
export STORAGE_S3_ACCESS_KEY_ID='KEY_ID'
export STORAGE_S3_SECRET_ACCESS_KEY='APPLICATION_KEY'
```

Le fichier `SHARED/storage.env.example` sert de modèle. Le premier test doit utiliser un petit fichier dans `campaigns/storage_test/`, puis vérifier upload, existence, hash, téléchargement et URL temporaire.
