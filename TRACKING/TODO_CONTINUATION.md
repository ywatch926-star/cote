# LACRIMAE dev10 — TODO DE CONTINUATION

> Point d'entrée obligatoire après toute migration de sandbox.
> Dernière mise à jour : 2026-09-09.

## État confirmé

Le dépôt est `https://github.com/kioka8877-ux/LACRIMAE`, branche `dev10`
(commit de référence `704800b`). dev10 est canonisé **bras armé du mode PUR**
de PERTURABO (`kioka8877-ux/PERTURABO`, `MONDES_FORGES/CLIPPING`) : le pack
PUR entre, le MP4 final sort, 100 % GitHub Actions.

Travail PUR réalisé sur la branche de travail `dev10-pur` (commits
`42a9ebc`, `61b719f` + lot 3) : BridgeClipper v2, F00-PUR ingest, onglet
PUR F03, rendu F04 parité, workflow `dev10_pur_render.yml`, bridge `--pur`,
docs (PUR_GATES / PUR_CAMPAIGN_LOG / PUR_IMPLEMENTATION / guide opérateur).

## Priorités canoniques

1. **Mode PUR — bras armé PERTURABO** (unique mission de dev10) :
   `F00-PUR → bridge --pur → F03 Preview ⚡ PUR → dev10_pur_render.yml`
2. **F00H (hook 2 s)** : implémenté, test réel REPORTÉ — non prioritaire.
   Reprendre via `TRACKING/F00H_GATES.md` quand décidé.
3. **Test réel Ranking dev9** : hérité de dev9, non exécuté. Non bloquant
   pour PUR — ne pas mélanger les assets.

## Prochaine étape exacte (PUR)

Exécuter le premier **E2E PUR réel** :

```text
1. GitHub Actions → "DEV10 PUR — Bras armé PERTURABO" (workflow_dispatch)
   inputs : pack_filter=pur_A01, canvas=9:16
2. Vérifier gates G0-G3 (logs F00-PUR) et P2 (MP4 artifact lac-pur-final)
3. Contrôle visuel : hook 0-3 s sans texte, overlay 2 lignes après le hook,
   zoom frame-exact ~8.62 s (A01), fade_to_black final
4. Journaliser dans TRACKING/PUR_CAMPAIGN_LOG.md (ligne pur-A01)
5. Tag canonique à la validation : pur-canon-v1
```

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
