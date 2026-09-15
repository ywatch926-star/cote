/* ═══════════════════════════════════════════════════════════════════
   caviarV2.js — Groupe 1 v2 : adaptateur pack v2 (partition F00D) → moteur

   La note technique PERTURABO (2026-09-15) définit le pack v2 : le geste
   vit dans `caviar_partition` (sortie F00D), pas dans `caviar` (v1). Les
   champs sont renommés : panels[] (au lieu de brolls[]), silence_trims[]
   (au lieu de jump_cuts[]), events.punch_ins[] (underscore), start_sec
   (au lieu de at_sec), broll_id sémantique (BLUR-01) au lieu du numéro.

   Rôle de cet adaptateur (UN SEUL fichier) :
     1. détecter le schéma (v2 / v1 / v0) — jamais d'échec sur les vieilles
        clés absentes (angle, cut_directives, text_payload…) ;
     2. normaliser `caviar_partition` en bloc v1 du moteur (`caviarRender.js`),
        qui applique déjà le Budget d'Attention, le flash ENTRÉE-seule, le
        SFX entrée-seule et le dépôt des excédents ;
     3. résoudre le registre sémantique : broll_id → fichier, avec compat du
        registre numéroté 1-4 (v1). PERTURABO ne voit jamais les fichiers.

   Zéro décision créative ici : F00D commande, le moteur exécute, le gate
   vérifie. Bloc absent → null (rendu historique à l'identique).
   ═══════════════════════════════════════════════════════════════════ */

/** Détecte la version du schéma d'un pack PUR.
 *  'v2' : caviar_partition (pack F00D caviar_bound)
 *  'v1' : caviar (notre bloc Groupe 3)
 *  'v0' : aucun bloc caviar — pack historique (rendu à l'identique)
 *  Les packs v2 NE contiennent PAS les vieilles clés (angle, cut_directives,
 *  reference_style, text_payload, submission_checklist) : on ne les exige
 *  jamais — la détection se fait par la présence des blocs, jamais par leur
 *  absence (piège de compat documenté dans la note §5). */
export function detectPackSchema(pack) {
  const p = pack && typeof pack === 'object' ? pack : {};
  if (p.caviar_partition && typeof p.caviar_partition === 'object') return 'v2';
  if (p.caviar && typeof p.caviar === 'object') return 'v1';
  return 'v0';
}

/** Résout un broll_id sémantique ('BLUR-01') via le registre.
 *  Le registre v2 attend un index `semantic` : { "BLUR-01": { file, sfx, … } }.
 *  Compat v1 : un id purement numérique ('1', '2'…) résout via `clips`.
 *  Retourne { file, sfx, entry_flash } ou null si introuvable → l'événement
 *  sera déposé au rendu (« pas de vidéo = pas de B-roll »). */
export function resolveSemanticBroll(brollId, registry) {
  if (!brollId || !registry || typeof registry !== 'object') return null;
  const id = String(brollId).trim();
  const semantic = registry.semantic && typeof registry.semantic === 'object' ? registry.semantic : null;
  if (semantic) {
    const hit = semantic[id] || semantic[id.toUpperCase()] || semantic[id.toLowerCase()];
    if (hit && typeof hit === 'object' && hit.file) {
      return { file: String(hit.file), sfx: String(hit.sfx || 'impact'), entry_flash: hit.entry_flash !== false };
    }
  }
  // Compat v1 : id purement numérique → registre numéroté `clips`.
  if (/^\d+$/.test(id)) {
    const clip = (registry.clips || {})[id];
    if (clip && typeof clip === 'object' && clip.file) {
      return { file: String(clip.file), sfx: String(clip.sfx || 'impact'), entry_flash: clip.entry_flash !== false };
    }
  }
  return null;
}

/** Normalise `caviar_partition` (v2) en bloc v1 du moteur.
 *  Mapping (note §3.2/§3.3 → caviarRender.js) :
 *    panels[]              → brolls[]      (start_sec→at_sec, broll_id résolu, crop_zoom/blur/panel transportés)
 *    silence_trims[]       → jump_cuts[]   (cut_at_sec = start de coupe, removes_sec)
 *    events.punch_ins[]    → punchins[]    (at_sec)
 *    events.smash_audio[]  → smash_audio[] (at_sec, duck_db, duration_sec)
 *  `extra` conserve les champs v2 non mappés (crop_zoom, blur_radius_px, panel,
 *  resolution_at, broll_id…) pour le rendu du panneau (Phase 3) et le gate.
 *  Retourne null si la partition est absente/inutilisable (pack v0 ou vide). */
export function normalizeCaviarPartition(partition, registry = null) {
  const p = partition && typeof partition === 'object' ? partition : null;
  if (!p) return null;

  // Tolérance documentée : le PACK v2 réel porte panels[] et smash_audio[] au
  // TOP de la partition (vérifié sur voxc-2), le MANIFESTE caviar.v1 décrit
  // events.broll/events.punch_ins/events.smash_audio. On accepte les DEUX.
  const panels = Array.isArray(p.panels) ? p.panels : [];
  const events = p.events && typeof p.events === 'object' ? p.events : {};
  const brollEvents = Array.isArray(events.broll) ? events.broll : [];
  const punchIns = [
    ...(Array.isArray(events.punch_ins) ? events.punch_ins : []),
    ...(Array.isArray(p.punch_ins) ? p.punch_ins : []),
  ];
  const smashAudio = [
    ...(Array.isArray(events.smash_audio) ? events.smash_audio : []),
    ...(Array.isArray(p.smash_audio) ? p.smash_audio : []),
  ];
  const silTrims = Array.isArray(p.silence_trims) ? p.silence_trims : [];

  const brolls = [...panels, ...brollEvents].map((panel) => {
    if (!panel || typeof panel !== 'object') return null;
    const resolved = resolveSemanticBroll(panel.broll_id, registry);
    return {
      at_sec: Number(panel.start_sec || 0),
      duration_frames: Number(panel.duration_frames || 0),
      numero: panel.broll_id ?? null,           // identité (sémantique v2)
      file: resolved ? resolved.file : '',       // '' → déposé au rendu (pas de vidéo = pas de B-roll)
      sfx: resolved ? resolved.sfx : String(panel.sfx || 'impact'),
      entry_flash: panel.entry_flash !== false,
      extra: {
        broll_id: panel.broll_id ?? null,
        emotion_requested: panel.emotion_requested || '',
        crop_zoom: Number(panel.crop_zoom || 0) || undefined,
        blur_radius_px: Number(panel.blur_radius_px || 0) || undefined,
        panel: panel.panel || undefined,
      },
    };
  }).filter(Boolean);

  const jumpCuts = silTrims.map((t) => ({
    cut_at_sec: Number(t.cut_at_sec ?? t.start_sec ?? 0),
    removes_sec: Number(t.removes_sec ?? t.duration_sec ?? 0),
  })).filter((t) => Number.isFinite(t.cut_at_sec) && Number.isFinite(t.removes_sec));

  const punchins = punchIns.map((z) => ({
    at_sec: Number(z.at_sec ?? z.start_sec ?? 0),
    scale_to: Number(z.scale_to || z.crop_zoom || 1.08),
    attack_frames: z.attack_frames, hold_frames: z.hold_frames, release_frames: z.release_frames,
  }));

  const smash = smashAudio.map((s) => ({
    at_sec: Number(s.at_sec ?? s.start_sec ?? 0),
    duck_db: Number(s.duck_db ?? -12),
    duration_sec: Number(s.duration_sec ?? 0.8),
  }));

  return {
    enabled: p.bound === true ? true : p.enabled !== false,
    source: 'f00d_partition',
    jump_cuts: jumpCuts,
    punchins,
    brolls,
    smash_audio: smash,
    extra: {
      run_id: p.run_id || null,
      resolution_at: Number(p.resolution_at || 0) || null,
      style: p.style || null,
      budget_state: p.budget_state || null,
    },
  };
}

/** Point d'entrée unique : un pack (v0/v1/v2) → bloc v1 pour le moteur.
 *  - v2 : caviar_partition normalisée (registre sémantique si fourni) ;
 *  - v1 : bloc caviar tel quel ;
 *  - v0 : null (rendu historique à l'identique). */
export function packToCaviarBlock(pack, registry = null) {
  const schema = detectPackSchema(pack);
  if (schema === 'v2') return normalizeCaviarPartition(pack.caviar_partition, registry);
  if (schema === 'v1') return pack.caviar;
  return null;
}

/** Bloc DÉJÀ extrait (entry.caviar ?? manifest.caviar) → bloc moteur.
 *  Le passthrough transporte la partition v2 brute OU le bloc v1 : on
 *  distingue par la forme (panels/silence_trims/events/bound = v2).
 *  Retourne null si raw est vide (rendu historique). */
export function toEngineBlock(raw, registry = null) {
  if (!raw || typeof raw !== 'object') return null;
  const looksV2 = Array.isArray(raw.panels) || Array.isArray(raw.silence_trims)
    || (raw.events && typeof raw.events === 'object') || raw.bound === true;
  return looksV2 ? normalizeCaviarPartition(raw, registry) : raw;
}
