# Guide opérationnel LACRIMAE dev6-B (v2)

## Principe

La branche dev6-B (évolution v2) ne lance pas de calcul GPU pendant la phase d’analyse. F01 AUSPEX examine la source localement, produit des mesures et recommande un profil. Les étapes lourdes ne sont exécutées que lorsqu’un compte GPU actif est disponible.

## Séquence de décision

AUSPEX ne cherche pas à imiter un modèle propriétaire. Il décrit la source avec des mesures observables. Une scène sombre avec beaucoup de clipping noir reçoit une recommandation réaliste ; une scène contrastée et saturée peut recevoir HDR ; une scène sombre à forte énergie peut recevoir Noctis. Le profil reste modifiable manuellement.

## Contrôle qualité

Un résultat n’est accepté que si la résolution et la cadence attendues sont respectées, si l’audio est conservé lorsqu’il existe, si les frames ne présentent pas de scintillement visible, si les visages ne deviennent pas cireux et si les contours ne développent pas de halos. Les métriques servent de signal d’alerte ; la décision finale se fait en visionnage.

## Test sans GPU

```bash
python3 ORACLE/auspex.py input.mp4 --output auspex.json
python3 ORACLE/universal_run.py --dry-run --root .test/v2 --campaign-id dry_run --source input.mp4 --profile auto
```

Le second appel ne doit pas contacter un worker GPU en mode `--dry-run`. Il sert à vérifier les chemins, le manifeste et les rapports.

## Test de production futur

Le premier essai après réactivation d’un compte GPU doit durer environ cinq secondes. Il doit utiliser la source originale et produire au minimum une sortie automatique, une sortie réaliste et une sortie HDR. Les trois campagnes doivent rester séparées.

## Règles anti-régression

Toute modification de dev6-B doit être committée avant un run. `dev6` n’est jamais utilisé comme zone d’essai. Les secrets restent dans un fichier d’environnement local. Les modèles sont placés dans le Volume modèles et les vidéos dans le Volume vidéo.
