HEISENBERG — BROLL/candidates (fiches d'ajout)
===============================================

Une fiche = un numéro candidat, proposé par PERTURABO ou l'opérateur :

```json
{
  "numero_candidat": "5",
  "fichier_suggere": "broll_05.mp4",
  "emotions": ["choc", "horreur"],
  "sfx": "boom",
  "decision_operateur": "PENDING"
}
```

L'opérateur tranche (PENDING → APPROVED/REJECTED). Une fiche APPROVED
devient une entrée du `registry.json` (numérotée, avec ses émotions),
et le fichier réel est déposé dans `FILES/`.
