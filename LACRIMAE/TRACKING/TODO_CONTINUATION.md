# LACRIMAE — TODO CONTINUATION

## Branche active

Le travail actif se fait sur **`dev6-B`** dans le dépôt `kioka8877-ux/LACRIMAE`. La branche `dev6` est stable et ne doit pas être modifiée par les essais. OMNIS_WATCH est un dépôt séparé et ne fait pas partie du développement actif.

## État général

| Domaine | État |
|---|---|
| Architecture DOMINUS HYPERFLUIDA | Fonctionnelle |
| RIFE 4.25 vers 120 FPS | Validé sur une source 30 FPS |
| GFPGAN v1.3 ciblé | Fonctionnel, stride facial configurable |
| AUSPEX PIXEL/TEMPORAL | Fonctionnel localement sans GPU |
| Profils ATOM-IC | HDR, réaliste, nocturne et viral disponibles |
| F07 CHROMA DOMINATUS | Fonctionnel |
| F08 TEMPORALIS CONSISTENTIA | Présent, garde transparente par défaut |
| F09 AETHER COMPOSITUM | À développer |
| Presets After Effects `.ffx` | Analyse de `cc2.ffx` effectuée |
| Modal | Déploiement validé sur `tekfugo`, Volumes à vérifier lors d’un nouveau compte |
| Documentation de continuité | À jour dans ce commit |

## Travaux terminés

- Création de la branche de travail `dev6-B` depuis l’ancien état `v2`.
- Conservation de `dev6` comme branche stable.
- Intégration d’AUSPEX dans F01 avec le mode `auto`.
- Ajout des profils `hdr_imperator`, `realistic_aurea`, `old_main_noctis` et `viral_imperator`.
- Ajout de F07 CHROMA DOMINATUS.
- Ajout des paramètres Motus Viral dans F08.
- Optimisation de F05 avec `frame_stride`.
- Déploiement v2 sur Modal et exécution d’une source 1920×1080 à 30 FPS vers 120 FPS.
- Analyse des références Topaz et des tutoriels d’édits 120 FPS.
- Analyse du preset After Effects `cc2.ffx`.
- Création du label GitHub `120 fps` sur LACRIMAE.

## Prochaine priorité : F09 AETHER COMPOSITUM

Créer une sous-frégate de compositing qui permet de choisir un preset sans modifier les autres Frégates. Les presets prévus sont :

- `silver_gray` : gris argenté et contraste métallique ;
- `dark` : sombre et cinématique avec protection des textures ;
- `warm` : tons chair protégés et lumières chaudes ;
- `viral_hdr` : impact fort, overlay lumineux et glow contrôlé ;
- `clean_realistic` : finition minimale et naturelle.

La pile de référence identifiée dans `cc2.ffx` est : Sharpen → Unsharp Mask → Magic Bullet Looks → S_Gradient → Compositing. La version headless doit reproduire cette logique avec des couches activables et des opacités contrôlées.

## Ordre de travail recommandé

1. Mettre à jour `CONFIG/atom_ic_profiles.json` avec une section de presets de compositing distincte du profil Enhance.
2. Ajouter F09 au registre Oracle et au contrat DOMINUS.
3. Implémenter une première version FFmpeg headless : courbes, levels, unsharp, extraction des hautes lumières, blur, screen/softlight, gradient, glow et grain.
4. Tester les couches localement sur les sorties déjà produites ; aucun GPU requis pour cette étape.
5. Ajouter la sélection `--preset` à Oracle sans remplacer la sélection `--profile`.
6. Générer une planche comparative source/HDR/realistic/dark/viral.
7. Utiliser un futur compte GPU uniquement pour un test de 5 secondes après validation CPU.
8. Vérifier le rendu en mouvement avant tout rendu long.

## Checklist avant chaque GPU

- [ ] Branche confirmée : `dev6-B`.
- [ ] `git status` vérifié.
- [ ] Source originale hashée.
- [ ] Orientation, résolution, FPS et audio identifiés.
- [ ] Rapport AUSPEX généré.
- [ ] Profil et preset justifiés.
- [ ] Compte Modal et workspace confirmés.
- [ ] Volumes vidéo et modèles listés.
- [ ] Poids RIFE et GFPGAN présents dans le Volume modèle.
- [ ] Test court prévu avant tout rendu long.

## Reprise après extinction du sandbox

```bash
gh repo clone kioka8877-ux/LACRIMAE /home/ubuntu/LACRIMAE_DEV6
cd /home/ubuntu/LACRIMAE_DEV6
git checkout dev6-B
git pull --ff-only origin dev6-B
cat CONTINUATION.md
cat TRACKING/TODO_CONTINUATION.md
cat TRACKING/DEV6B_GATES.md
```

Le nouveau sandbox doit recréer `.env.modal` localement. Il ne doit jamais chercher les secrets dans GitHub. Il doit vérifier l’espace Modal et les Volumes avant de lancer Oracle.

## Règles de sécurité et de coût

Les secrets, modèles lourds, vidéos et caches ne doivent pas être commités. Les analyses textuelles, contrats, rapports et configurations peuvent être versionnés. Un nouveau compte Modal peut avoir des Volumes vides même si les noms existent déjà ; la présence des fichiers doit être vérifiée explicitement.
