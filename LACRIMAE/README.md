# LACRIMAE — Fleet of Frigates v2

> *For the Angel's Tears shall become gold.*

LACRIMAE dev6-B est la branche active (héritage v2) de la flotte vidéo **DOMINUS HYPERFLUIDA**. Elle vise une qualité perçue supérieure grâce à la combinaison de reconstruction de détail, restauration par zones, fluidité temporelle, montage dynamique et finition cinématique. La branche `dev6` reste la version stable de secours ; aucune expérimentation v2 ne doit la modifier.

## Architecture v2

```text
source vidéo
    │
    ▼
F00 PORTA INGRESSUS
    │
    ▼
F01 AUSPEX OCULUS
  ├── AUSPEX PIXEL : luminance, contraste, saturation, contours, bruit
  └── AUSPEX TEMPORAL : mouvement, pics, stabilité et profil recommandé
    │
    ▼
ATOM-IC ENHANCE
  ├── F03 APOTHECA RESTAURA
  ├── F04 FORGE TEXTURA
  └── F05 LIBRARIUS FACIES
    │
    ▼
ATOM-IC MOTUS VIRAL
  ├── F02 MOTUS RIFE : interpolation vers 120 FPS
  └── F08 TEMPORALIS CONSISTENTIA : garde/stabilisation temporelle
    │
    ▼
F06 LUMEN IGNIS → F07 CHROMA DOMINATUS
    │
    ▼
F10 CUSTOS RESTITUTIO
```

| Frégate | Mission | Exécution |
|---|---|---|
| **F00 PORTA INGRESSUS** | Valider la source et ses métadonnées. | Oracle local |
| **F01 AUSPEX OCULUS** | Mesurer la vidéo et choisir un profil. | CPU local, sans GPU |
| **F02 MOTUS RIFE** | Interpoler la cadence jusqu’à 120 FPS. | GPU distant |
| **F03 APOTHECA RESTAURA** | Débruiter et nettoyer la compression. | GPU distant |
| **F04 FORGE TEXTURA** | Renforcer texture, contraste et contours. | GPU distant |
| **F05 LIBRARIUS FACIES** | Restaurer les visages avec un masque ciblé. | GPU distant |
| **F06 LUMEN IGNIS** | Régler lumière, contraste et finition. | GPU distant |
| **F07 CHROMA DOMINATUS** | Appliquer une signature colorimétrique. | GPU distant |
| **F08 TEMPORALIS CONSISTENTIA** | Contrôler le scintillement et les warps. | GPU distant |
| **F10 CUSTOS RESTITUTIO** | Récupérer, vérifier et sceller la sortie. | Oracle local |

## Analyse adaptative

AUSPEX fonctionne localement et ne consomme pas de crédit GPU. Il mesure la luminance moyenne et sa dispersion, la saturation, les zones noires et blanches écrêtées, la netteté Laplacienne, la densité de contours et la différence moyenne entre frames échantillonnées.

```bash
python3 ORACLE/auspex.py /chemin/scene.mp4 --output /tmp/auspex.json
```

Le résultat recommande un profil parmi `hdr_imperator`, `realistic_aurea`, `old_main_noctis` et `viral_imperator`, ainsi qu’un mode `cinematic` ou `viral` selon le mouvement mesuré. Le mode automatique du parcours est prêt pour un futur compte GPU :

```bash
python3 ORACLE/universal_run.py \
  --root .test/v2 \
  --campaign-id production_test \
  --source /chemin/scene.mp4 \
  --profile auto \
  --target-fps 120
```

## Profils de finition

`hdr_imperator` maximise l’impact visuel avec un contraste et une saturation contrôlés. `realistic_aurea` protège les tons chair et vise une restitution naturelle. `old_main_noctis` cible les montages sombres et cinématiques. `viral_imperator` ajoute expérimentalement un blending et un motion blur Motus faibles. Les profils pilotent séparément restauration, texture, visage, lumière, chroma, temporalité et Motus.

## ATOM-IC ENHANCE et MOTUS VIRAL

Enhance et 4K sont deux opérations différentes. Enhance vise la qualité générale : compression, détail, visage, textures, contraste et couleurs. L’upscale 4K augmente la taille de sortie mais ne garantit pas une reconstruction crédible.

Motus Viral traite la fluidité au sens large. RIFE crée des images intermédiaires ; le rendu viral peut également dépendre du frame blending, du motion blur, des speed ramps, des cuts synchronisés, des zooms, des shakes, des flashes et du compositing. F08 sait maintenant lire `motus.frame_blend` et `motus.motion_blur` ; ils restent à zéro dans les profils cinéma et sont faibles dans `viral_imperator` jusqu’à validation contre le ghosting.

## Stockage et portabilité

Le code est versionné sur GitHub. Les vidéos et les modèles sont stockés dans des Volumes indépendants. Les identifiants et fichiers d’environnement restent locaux et ne doivent jamais être commités. Le projet peut être redéployé sur un nouveau compte GPU en récupérant le code, les modèles, les variables et les Volumes.

## Développement sans crédits Modal

Lorsque les crédits GPU sont épuisés, le développement continue localement avec AUSPEX, FFmpeg, OpenCV, les profils, les rapports, les comparaisons d’images et les tests de contrats. Les étapes RIFE et GFPGAN ne doivent pas être lancées sans un compte GPU actif.

La branche dev6-B utilise les rendus existants comme références, mais une nouvelle campagne doit toujours repartir de la source originale. Une sortie déjà traitée ne doit pas devenir silencieusement l’entrée d’une autre comparaison.

## Validation

Chaque campagne doit enregistrer la source, son hash, la résolution, la cadence, la durée, l’audio, le profil choisi, les paramètres, les rapports par frégate et le hash de la sortie. Les critères prioritaires sont le détail naturel du visage, les cheveux et vêtements lisibles, les noirs non bouchés, l’absence de halos, la stabilité temporelle et la qualité du mouvement.

## Suivi opérationnel

Le TODO de reprise est disponible dans [`TRACKING/TODO_CONTINUATION.md`](TRACKING/TODO_CONTINUATION.md). Les gates de validation sont définis dans [`TRACKING/DEV6B_GATES.md`](TRACKING/DEV6B_GATES.md), et le registre de campagnes se trouve dans [`TRACKING/dev6b_campaign_ledger.json`](TRACKING/dev6b_campaign_ledger.json). Le guide opératoire est dans [`docs/V2_OPERATIONS_GUIDE.md`](docs/V2_OPERATIONS_GUIDE.md), le contrat dans [`docs/DOMINUS_HYPERFLUIDA_V2_CONTRACT.md`](docs/DOMINUS_HYPERFLUIDA_V2_CONTRACT.md) et le panneau dans [`docs/V2_CONTROL_PANEL.md`](docs/V2_CONTROL_PANEL.md).

## Documentation associée

La feuille de route expérimentale est disponible dans [`V2_EVOLUTION_ROADMAP.md`](V2_EVOLUTION_ROADMAP.md). Les objectifs issus des références Topaz et des tutoriels de fluidité sont documentés dans [`ANALYSE_TROIS_REFERENCES_TOPAZ.md`](ANALYSE_TROIS_REFERENCES_TOPAZ.md) et [`ANALYSE_FLUIDITE_VIRALE_ET_CIBLE_V2.md`](ANALYSE_FLUIDITE_VIRALE_ET_CIBLE_V2.md).

## État de dev6-B

La branche est prête pour une validation CPU de l’analyse et des contrats. La reconstruction générale équivalente à Proteus, la stabilisation temporelle active et l’édition virale automatisée restent les prochaines briques à consolider avant un nouveau run GPU de production.
