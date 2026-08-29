# 🔧 TECHNICAL HANDOFF — LACRIMAE dev6-C

## Contexte

Ce document décrit tout ce qui a été fait sur la branche `dev6-C` du dépôt `kioka8877-ux/LACRIMAE`. L'objectif est de permettre à un autre agent/sandbox de recréer et push cette branche.

---

## 1. Structure de la branche

```
dev6-C (basée sur dev6-B)
├── F09_AETHER/
│   ├── CODEBASE/
│   │   └── lac_f09_aether.py          # Moteur de compositing v2
│   ├── PRESETS/
│   │   └── compositing_presets.json    # 6 presets reconstruits depuis les .aep CC
│   └── README.md                       # Documentation F09
├── CONFIG/
│   └── atom_ic_profiles.json           # Mis à jour v1.2.0 avec compositing_preset
├── ORACLE/
│   ├── oracle.py                       # F09 ajouté aux STAGES
│   ├── universal_run.py                # F09 exécuté localement avec sélection auto
│   └── universal_frigate_contract.md   # Contrat mis à jour
└── outputs/
    └── aether_v2_clean_realistic.mp4   # Vidéo de test (7.9 MB)
```

---

## 2. Fichiers à copier depuis `ywatch926-star/cote` branche `dev6-C`

Le code complet est disponible sur : `https://github.com/ywatch926-star/cote/tree/dev6-C`

### Fichiers principaux à copier :

**F09 AETHER COMPOSITUM (nouveau) :**
- `LACRIMAE/F09_AETHER/CODEBASE/lac_f09_aether.py`
- `LACRIMAE/F09_AETHER/PRESETS/compositing_presets.json`
- `LACRIMAE/F09_AETHER/README.md`

**Fichiers modifiés :**
- `LACRIMAE/CONFIG/atom_ic_profiles.json`
- `LACRIMAE/ORACLE/oracle.py`
- `LACRIMAE/ORACLE/universal_run.py`
- `LACRIMAE/ORACLE/universal_frigate_contract.md`
- `LACRIMAE/.gitignore`

**Fichiers de test (optionnels) :**
- `outputs/aether_v2_clean_realistic.mp4`

---

## 3. Étapes pour recréer la branche dev6-C

### Étape 1 : Cloner le dépôt
```bash
git clone https://github.com/kioka8877-ux/LACRIMAE.git
cd LACRIMAE
```

### Étape 2 : Créer la branche dev6-C depuis dev6-B
```bash
git checkout dev6-B
git checkout -b dev6-C
```

### Étape 3 : Copier les fichiers depuis cote
```bash
# Option A : Clone temporaire
git clone -b dev6-C https://github.com/ywatch926-star/cote.git /tmp/cote
cp -r /tmp/cote/LACRIMAE/F09_AETHER ./F09_AETHER
cp /tmp/cote/LACRIMAE/CONFIG/atom_ic_profiles.json ./CONFIG/
cp /tmp/cote/LACRIMAE/ORACLE/oracle.py ./ORACLE/
cp /tmp/cote/LACRIMAE/ORACLE/universal_run.py ./ORACLE/
cp /tmp/cote/LACRIMAE/ORACLE/universal_frigate_contract.md ./ORACLE/
cp /tmp/cote/LACRIMAE/.gitignore ./.gitignore

# Option B : Télécharger les fichiers individuels via GitHub API
# (voir section 5)
```

### Étape 4 : Ajouter les fichiers et committer
```bash
git add F09_AETHER/ CONFIG/atom_ic_profiles.json ORACLE/ .gitignore
git commit -m "feat(F09): AETHER COMPOSITUM v2 — presets from real CC .aep analysis

- Extracted actual effect chain from AE26 and Mreditz .aep files
- Real chain: S_Sharpen(×3) → BCC Unsharp Mask(×3) → MB Looks (ACES→Rec.709) → S_Glow(×2)
- 6 presets: clean_realistic, mreditz_giveaway, silver_gray, dark, warm, viral_hdr
- filter_complex support for glow bloom (split+blend)
- ACES 1.0.3→Rec.709 color pipeline approximation"

git push origin dev6-C
```

---

## 4. Ce qui a été fait (détail technique)

### 4.1 Analyse des projets .aep de la release CC

J'ai extrait les données binaires des projets After Effects :

**Projet AE26 (AEditz Quality CC 2) :**
- Chaîne : S_Sharpen ×3 → BCC Unsharp Mask ×3 → MB LookSuite3 → S_Glow ×2
- OCIO : ACES 1.0.3 → Output - Rec.709
- Base Color Profile : Rec.709 Gamma 2.4
- Paramètres extraits : Sharpen Amp ~1.57, Edge Threshold 0.0339, BCC Amount ~15.77, BCC Threshold 42, BCC Pre Smoothing 42, BCC Preserve Contrast 32.5, BCC Gamma 130

**Projet Mreditz x AEditz CC Giveaway :**
- Chaîne : Brightness & Contrast → CurvesCustom → Unsharp Mask → BCC Unsharp Mask
- Plus simple mais efficace

### 4.2 F09 AETHER COMPOSITUM v2

**Moteur (`lac_f09_aether.py`) :**
- Supporte les filtres simples (-vf) et complexes (-filter_complex)
- Gère le glow via split+boxblur+screen blend avec labels uniques
- Modulation d'opacité pour eq/colorbalance
- QA automatique (vérifie codec, resolution, tags suspects)

**Presets (`compositing_presets.json`) :**

| Preset | Couches | Description |
|---|---|---|
| clean_realistic | 9 | Chaîne AE26 complète (S_Sharpen×3 + BCC×3 + ACES + S_Glow×2) |
| mreditz_giveaway | 5 | Chaîne Mreditz (B&C + Curves + Unsharp + BCC + ACES tint) |
| silver_gray | 5 | Désaturation ACES, contraste métallique |
| dark | 6 | Contraste cinématique ACES, glow subtil |
| warm | 5 | Tons chair protégés, chaleur ACES |
| viral_hdr | 6 | Impact maximal, glow prononcé |

### 4.3 Intégration Oracle

- F09_AETHER_COMPOSITUM ajouté aux STAGES (entre F08 et F10)
- `universal_run.py` exécute F09 localement avec sélection auto du preset depuis le profil ATOM
- Le preset est choisi via `atom_ic_profiles.json` → `compositing_preset`

---

## 5. Téléchargement des fichiers via GitHub API (si pas de git)

Si tu ne peux pas cloner, tu peux télécharger les fichiers individuels :

```bash
# Fonction pour télécharger un fichier depuis cote
download_file() {
  local path="$1"
  curl -sL "https://raw.githubusercontent.com/ywatch926-star/cote/dev6-C/$path" -o "$path"
  mkdir -p "$(dirname "$path")"
}

# Télécharger tous les fichiers
download_file "LACRIMAE/F09_AETHER/CODEBASE/lac_f09_aether.py"
download_file "LACRIMAE/F09_AETHER/PRESETS/compositing_presets.json"
download_file "LACRIMAE/F09_AETHER/README.md"
download_file "LACRIMAE/CONFIG/atom_ic_profiles.json"
download_file "LACRIMAE/ORACLE/oracle.py"
download_file "LACRIMAE/ORACLE/universal_run.py"
download_file "LACRIMAE/ORACLE/universal_frigate_contract.md"
download_file "LACRIMAE/.gitignore"
```

---

## 6. Tests effectués

| Preset | QA | Couches | Temps | Taille | Filtre |
|---|---|---|---|---|---|
| clean_realistic | ✅ PASS | 9/9 | 103s | 8.0 MB | filter_complex |
| mreditz_giveaway | ✅ PASS | 5/5 | 40s | 4.0 MB | vf_chain |
| dark | ✅ PASS | 6/6 | 70s | 4.1 MB | filter_complex |

**Vidéo source** : `.test/rife_input_5s.mp4` (1920×1080, H.264, 30fps, 5s, 6.5 MB)

---

## 7. Prochaines étapes

1. **Corriger l'oversharpening** : Réduire les passes de sharpen (6 → 1-2 max)
2. **Corriger l'oversaturation** : Réduire la saturation dans le grade ACES
3. **Ajouter du grain organique** : Le v2 l'a viré, le v1 en avait
4. **Intégrer Real-ESRGAN** : Neural network open source pour débruitage/upscaling (remplace Topaz)
5. **Tester sur vidéo longue** : La vidéo test fait 5s, il faut tester sur 30s+

---

## 8. Notes importantes

- **Le repo `kioka8877-ux/LACRIMAE`** n'est PAS connecté à Freebuff. Il faut le reconnecter ou push manuellement.
- **Le repo `ywatch926-star/cote`** EST connecté à Freebuff. Le code y est déjà sur dev6-C.
- **Les archives RAR de la release CC** sont protégées par mot de passe. Les screenshots Topaz/HandBrake/AE ne sont pas extractibles sans le mot de passe.
- **FFmpeg seul ne peut pas reproduire le look AE**. Les plugins AE (S_Sharpen, BCC, MB Looks, S_Glow) ont des algorithmes propriétaires. Notre approximation est "bonne pas géniale".

---

*Document généré le 29 août 2026 par Buffy (Codebuff)*
