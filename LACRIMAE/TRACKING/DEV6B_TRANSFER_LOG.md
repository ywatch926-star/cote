# LACRIMAE dev6-B — JOURNAL DE TRANSFERT

## Principe

Le code et les documents sont versionnés sur GitHub. Les modèles et les vidéos sont transférés séparément vers les Volumes. Les secrets restent dans un fichier d’environnement local et ne sont jamais copiés dans le dépôt.

## Cartographie des artefacts

| Artefact | Emplacement recommandé | Versionné sur GitHub | Vérification |
|---|---|---:|---|
| Code Oracle et worker | Dépôt LACRIMAE, branche dev6-B | Oui | `git checkout dev6-B` |
| Configurations JSON | `CONFIG/` | Oui | Validation JSON |
| Guides et contrats | `README.md`, `docs/`, `TRACKING/` | Oui | Lecture au démarrage |
| Poids RIFE | Volume modèles Modal | Non | Présence et hash du fichier |
| Poids GFPGAN | Volume modèles Modal | Non | Présence et hash du fichier |
| Vidéo originale | Volume vidéo Modal | Non | Hash avant transfert |
| Intermédiaires | Volume vidéo, campagne isolée | Non | Rapport de Frégate |
| `.env.modal` | Sandbox local uniquement | Non | Permissions privées |
| Presets `.ffx` privés | Stockage local contrôlé | Non | Analyse ou transfert explicite |

## Procédure de transfert

1. Vérifier la branche `dev6-B` et le commit avant tout transfert.
2. Calculer le hash SHA-256 des modèles et de la vidéo source.
3. Vérifier que le workspace Modal et les deux Volumes correspondent au compte actif.
4. Vérifier la présence réelle des poids dans le Volume modèles ; un Volume vide ne doit jamais être supposé prêt.
5. Envoyer la source originale sous un identifiant de campagne unique.
6. Exécuter F01 AUSPEX avant toute étape GPU.
7. Conserver chaque intermédiaire dans son propre dossier de campagne.
8. Télécharger F10 et son rapport après scellement.

## Changement de compte Modal

Lorsqu’un compte atteint sa limite, le code ne doit pas être reconstruit conceptuellement. Il faut charger le nouveau `.env.modal`, vérifier son workspace, redéployer l’application si nécessaire, recréer ou rattacher les Volumes, puis transférer les modèles et relancer uniquement depuis la source originale. Les noms de Volumes ne garantissent pas leur contenu.

## Récupération depuis un nouveau sandbox

Le prochain sandbox doit cloner le dépôt, sélectionner `dev6-B`, lire `CONTINUATION.md`, vérifier `TRACKING/TODO_CONTINUATION.md`, puis consulter ce journal avant d’utiliser Modal. Les vidéos et modèles ne doivent pas être recherchés dans GitHub.

## Incident connu

Sur le workspace `tekfugo`, le déploiement initial a réussi mais le Volume modèles était vide. RIFE a échoué avant rendu jusqu’au transfert de RIFE 4.25 et GFPGAN v1.3. Cet incident doit rester un contrôle obligatoire dans toute nouvelle campagne.
