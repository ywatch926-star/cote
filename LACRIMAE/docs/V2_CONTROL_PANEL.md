# Panneau de contrôle LACRIMAE dev6-B (v2)

## État de la flotte

| Zone | État | Prochaine action |
|---|---|---|
| `dev6` stable | Protégée | Ne pas modifier |
| `dev6-B` active (héritage v2) | Active | Développer et tester sans GPU |
| AUSPEX | Implémenté en CPU | Calibrer les seuils sur plusieurs scènes |
| Enhance général | Partiel | Ajouter une reconstruction plus puissante |
| RIFE 4.25 | Validé | Réutiliser sur le prochain compte GPU |
| GFPGAN v1.3 | Validé | Régler le poids et le fondu par profil |
| Chroma Dominatus | Implémenté | Calibrer noirs, peau et hautes lumières |
| Motus Viral | F08 implémenté partiellement | Tester `viral_imperator`, puis ajouter speed ramps et montage |
| Modal | Crédits épuisés | Aucun run GPU avant nouveau compte actif |

## Suivi et gates

Le suivi opérationnel est centralisé dans `TRACKING/TODO_CONTINUATION.md`, `TRACKING/DEV6B_GATES.md` et `TRACKING/dev6b_campaign_ledger.json`. Toute campagne doit passer G0 à G9 et conserver ses rapports sans écraser une tentative précédente.

## Profils

`hdr_imperator` vise l’impact, `realistic_aurea` vise le naturel, `old_main_noctis` vise le sombre cinématique et `viral_imperator` active un blending et un motion blur faibles. Le mode `auto` laisse AUSPEX sélectionner un profil visuel ; le mode viral peut être sélectionné manuellement lorsque le montage le justifie.

## Critères de passage

Une Frégate passe la validation si elle conserve la résolution et la cadence, respecte l’audio présent, augmente le détail sans peau cireuse, évite les halos, garde les noirs lisibles et reste stable entre les frames. Une métrique élevée de netteté seule ne suffit pas.

## Gestion du calcul

Le développement CPU, l’analyse, les rapports et les tests de validation des presets sont autorisés immédiatement. Les modèles RIFE et GFPGAN ne doivent être exécutés que sur un compte GPU actif. Le premier nouveau run doit rester court et produire plusieurs profils depuis la même source originale.
