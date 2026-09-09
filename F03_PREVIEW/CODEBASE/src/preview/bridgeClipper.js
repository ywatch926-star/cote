/* ═══════════════════════════════════════════════════════════════════
   bridgeClipper.js — PERTURABO Mode PUR → LACRIMAE ranking_manifest
   
   Parses montage_instructions.json (from PERTURABO F06_DIRECTOR)
   and converts it into the ranking_manifest format that dev9/dev10
   RankingCompilationComposition understands.
   
   Also supports production_pack.json (from F05_PACKAGER) as input.
   v2 : parsePurPack() consomme les packs PUR complets
   (production_pack_pur_*.json, v2.0.0-viral : copywriting +
   montage_instructions embarquees) → manifeste dev10.pur.v1
   consomme par PurPackComposition (F03 Preview + F04 PICTOR).
   
   PERTURABO outputs:
     montage_instructions.json → hook, body (cuts, zooms, text), outro
     production_pack.json → identite, source, angle, cut, style, text_payload
     production_pack_pur_*.json → source, copywriting, montage_instructions
   
   LACRIMAE expects:
     ranking_manifest → entries[], narrative{}, total_frames, fps
     pur_manifest (dev10.pur.v1) → entries[], narrative.overlay{}, pur{}
   ═══════════════════════════════════════════════════════════════════ */

const clamp = (value, min, max, fallback) => {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
};

/**
 * Parse a montage_instructions.json from PERTURABO F06_DIRECTOR
 * and return a ranking_manifest compatible with RankingCompilationComposition.
 *
 * @param {object} instructions - The montage_instructions.json content
 * @param {object} options - { fps: 30, clipFiles: ['clips/clip1.mp4', ...] }
 * @returns {object} ranking_manifest
 */
export function parseMontageInstructions(instructions, options = {}) {
  const fps = options.fps || 30;
  const clipFiles = options.clipFiles || [];

  if (!instructions || typeof instructions !== 'object') {
    return createEmptyManifest(fps);
  }

  const segment = instructions.segment || {};
  const hook = instructions.hook || {};
  const body = instructions.body || {};
  const outro = instructions.outro || {};
  const textPayload = instructions.text_payload || {};
  const style = instructions.style || {};
  const platformRules = instructions.platform_rules || {};

  // Calculate durations
  const hookDuration = hook.duration_sec || 3;
  const bodyDuration = body.duration_sec || (segment.duration_sec || 30) - hookDuration;
  const outroDuration = outro.duration_sec || 2;
  const totalDuration = hookDuration + bodyDuration + outroDuration;

  // Build entries from cuts (body cuts define the ranking segments)
  const cuts = body.cuts || [];
  const entries = cuts.map((cut, index) => {
    const rank = cuts.length - index; // countdown from N to 1
    const duration = cut.duration_sec || 3;
    const clipFile = clipFiles[index] || clipFiles[0] || '';

    // B-roll from body.text_overlays or body.zooms
    const broll = extractBrollForSegment(index, instructions);

    // Anti-detection settings
    const antiDetection = extractAntiDetection(instructions);

    return {
      rank,
      source_id: `pur_rank_${rank}`,
      clip_file: clipFile,
      duration_seconds: duration,
      label_words: extractLabelWords(textPayload, index, rank),
      label: extractLabelText(textPayload, index, rank),
      number_color: rank === 1 ? '#FFD400' : '#FF4444',
      number_size: rank === 1 ? 56 : 42,
      label_size: rank === 1 ? 28 : 22,
      sfx: extractSfx(index, instructions),
      broll: broll,
      anti_detection: antiDetection,
      role: rank === 1 ? 'final_rank' : 'rank_entry',
    };
  });

  // Build narrative from text_payload
  const narrative = {
    title_words: extractTitleWords(textPayload),
    category: style.pacing || '',
    final_label: textPayload.cta_text || '',
    global_controls: {
      title_scale: 1,
      number_scale: 1,
      label_scale: 1,
      clip_audio: true,
      list_x_pct: 5,
      list_y_pct: 25,
      list_spacing: 2,
      title_size: 42,
      title_x_pct: 50,
      title_y_pct: 5,
      title_align: 'center',
      // PUR mode additions
      layout: 'fullscreen', // 'fullscreen' or 'split'
      hook_duration: hookDuration,
      body_duration: bodyDuration,
      outro_duration: outroDuration,
      energy_level: style.energy_level || 'intense',
      cut_density: style.cut_density || 10,
    },
    font_family: 'Arial Black, sans-serif',
  };

  return {
    schema_version: 'dev10.pur.v1',
    mode: 'ranking_compilation',
    fps,
    narrative,
    entries,
    rank_count: entries.length,
    final_rank: entries.find(e => e.rank === 1) || null,
    total_frames: Math.round(totalDuration * fps),
    duration_seconds: totalDuration,
    // PUR-specific metadata
    pur: {
      source: segment.source_url || '',
      platform: platformRules.platform || 'youtube_shorts',
      hook: {
        type: hook.type || 'statement',
        template: hook.template || '',
        duration_sec: hookDuration,
        zoom: hook.zoom || {},
        text_overlay: hook.text_overlay || {},
      },
      energy_curve: body.energy_curve || [],
      transitions: body.transitions || [],
      compliance: instructions.compliance || {},
    },
  };
}

/**
 * Parse a production_pack.json from PERTURABO F05_PACKAGER
 * and return a ranking_manifest.
 *
 * @param {object} pack - The production_pack.json content
 * @param {object} options - { fps: 30, clipFiles: [...] }
 * @returns {object} ranking_manifest
 */
export function parseProductionPack(pack, options = {}) {
  const fps = options.fps || 30;
  const clipFiles = options.clipFiles || [];

  if (!pack || typeof pack !== 'object') {
    return createEmptyManifest(fps);
  }

  const source = pack.source || {};
  const cutDirectives = pack.cut_directives || {};
  const textPayload = pack.text_payload || {};
  const style = pack.reference_style || {};
  const angle = pack.angle || {};
  const segments = source.suggested_segments || [];

  // Build entries from suggested segments
  const entries = segments.map((seg, index) => {
    const rank = segments.length - index;
    const duration = (seg.end_sec || 30) - (seg.start_sec || 0);
    const clipFile = clipFiles[index] || clipFiles[0] || '';

    return {
      rank,
      source_id: `pack_rank_${rank}`,
      clip_file: clipFile,
      duration_seconds: Math.max(0.1, duration),
      label_words: extractLabelWords(textPayload, index, rank),
      label: extractLabelText(textPayload, index, rank),
      number_color: rank === 1 ? '#FFD400' : '#FF4444',
      number_size: rank === 1 ? 56 : 42,
      label_size: rank === 1 ? 28 : 22,
      sfx: { enabled: false, file: '', volume: 0.8 },
      broll: null,
      anti_detection: null,
      role: rank === 1 ? 'final_rank' : 'rank_entry',
    };
  });

  const totalDuration = entries.reduce((sum, e) => sum + e.duration_seconds, 0);

  return {
    schema_version: 'dev10.pur.v1',
    mode: 'ranking_compilation',
    fps,
    narrative: {
      title_words: extractTitleWords(textPayload),
      category: style.pacing || '',
      final_label: textPayload.cta_text || '',
      global_controls: {
        title_scale: 1,
        number_scale: 1,
        label_scale: 1,
        clip_audio: true,
        list_x_pct: 5,
        list_y_pct: 25,
        list_spacing: 2,
        title_size: 42,
        title_x_pct: 50,
        title_y_pct: 5,
        title_align: 'center',
        layout: 'fullscreen',
      },
      font_family: 'Arial Black, sans-serif',
    },
    entries,
    rank_count: entries.length,
    final_rank: entries.find(e => e.rank === 1) || null,
    total_frames: Math.round(totalDuration * fps),
    duration_seconds: totalDuration,
    pur: {
      source: source.video_url || '',
      platform: pack.cibles?.target_platform || 'youtube',
      angle_family: angle.angle_family || '',
      emotion_mode: angle.emotion_mode || '',
    },
  };
}

// ─── Helpers ──────────────────────────────────────────────────────

function createEmptyManifest(fps) {
  return {
    schema_version: 'dev10.pur.v1',
    mode: 'ranking_compilation',
    fps,
    narrative: { title_words: [], category: '', final_label: '', global_controls: {}, font_family: 'Arial Black, sans-serif' },
    entries: [],
    rank_count: 0,
    final_rank: null,
    total_frames: 0,
    duration_seconds: 0,
    pur: {},
  };
}

function extractTitleWords(textPayload) {
  const titles = textPayload.titles || [];
  if (titles.length > 0) {
    const best = titles[0]; // rank 1 title
    const text = best.text || '';
    const words = text.trim().split(/\s+/).slice(0, 4);
    return words.map((w, i) => ({
      text: w,
      color: i === 0 ? '#FFD400' : '#FFFFFF',
    }));
  }
  // Fallback: use on_screen_text
  const ost = textPayload.on_screen_text || '';
  if (ost) {
    return ost.trim().split(/\s+/).slice(0, 4).map((w, i) => ({
      text: w,
      color: i === 0 ? '#FFD400' : '#FFFFFF',
    }));
  }
  return [{ text: 'TOP', color: '#FFD400' }, { text: 'MOMENTS', color: '#FFFFFF' }];
}

function extractLabelWords(textPayload, index, rank) {
  const titles = textPayload.titles || [];
  const title = titles[index] || titles[0] || {};
  const text = title.text || `Rank ${rank}`;
  const words = text.trim().split(/\s+/).slice(0, 4);
  return words.map(w => ({ text: w, color: '#FFFFFF' }));
}

function extractLabelText(textPayload, index, rank) {
  const titles = textPayload.titles || [];
  const title = titles[index] || titles[0] || {};
  return title.text || `Rank ${rank}`;
}

function extractSfx(index, instructions) {
  const body = instructions.body || {};
  const transitions = body.transitions || [];
  // Find a transition near this cut
  const transition = transitions[index] || transitions[0];
  if (transition) {
    return {
      enabled: true,
      file: transition.sound_effect?.type || 'whoosh.mp3',
      volume: 0.8,
    };
  }
  return { enabled: false, file: '', volume: 0.8 };
}

function extractBrollForSegment(index, instructions) {
  // In PERTURABO's format, B-roll is not explicitly in montage_instructions
  // but can be inferred from text_overlays or body content
  // For now, return null (no B-roll by default)
  return null;
}

function extractAntiDetection(instructions) {
  // PERTURABO's anti_detection is in the production_pack, not montage_instructions
  // Return default anti-detection settings
  return {
    mirror: false,
    zoom: { type: 'slow_push_in', start_pct: 100, end_pct: 108 },
    speed: 1.0,
    crop: { top_pct: 0, bottom_pct: 0, left_pct: 0, right_pct: 0 },
  };
}

// ═══════════════════════════════════════════════════════════════════
// v2 — Packs PUR complets (production_pack_pur_*.json, F06_DIRECTOR)
// ═══════════════════════════════════════════════════════════════════

const PUR_CANVAS = {
  '9:16': { width: 1080, height: 1920 },
  '16:9': { width: 1920, height: 1080 },
  '1:1': { width: 1080, height: 1080 },
};

/**
 * Parse un pack PUR complet (PERTURABO F06_DIRECTOR, montage v2.0.0-viral)
 * et retourne un manifeste dev10.pur.v1 pour PurPackComposition.
 *
 * Le pack contient : source (vod + cut), copywriting (overlay_title),
 * montage_instructions (segment, hook, body{cuts,zooms,text_overlays,audio},
 * outro, anti_detection, platform_rules, style).
 *
 * @param {object} pack - Le production_pack_pur_*.json
 * @param {object} options - { fps: 30, clipFiles: ['clips/pur_A01.mp4'], canvas: '9:16' }
 * @returns {object} manifeste dev10.pur.v1
 */
export function parsePurPack(pack, options = {}) {
  const fps = options.fps || 30;
  const clipFiles = options.clipFiles || [];
  if (!pack || typeof pack !== 'object') return createEmptyPurManifest(fps);

  const mi = pack.montage_instructions || {};
  const segment = mi.segment || pack.source || {};
  const hook = mi.hook || {};
  const body = mi.body || {};
  const outro = mi.outro || {};
  const style = mi.style || {};
  const platformRules = mi.platform_rules || {};
  const mainTitle = (body.text_overlays && body.text_overlays.main_title) || {};

  // Copywriting v2 (copywriting.overlay_title) avec repli text_payload legacy
  const overlayLines = extractOverlayLines(pack.copywriting || pack.text_payload || {});

  const hookDuration = clamp(hook.duration_sec ?? platformRules.hook_duration_sec ?? 3, 0, 15);
  const sourceDuration = clamp(
    Number(segment.duration_sec) || (Number(segment.end_sec) - Number(segment.start_sec)) || 30,
    0.5, 600);
  const bodyDuration = Number(body.duration_sec) || Math.max(1, sourceDuration - hookDuration);
  const outroDuration = clamp(outro.duration_sec ?? 1, 0, 5);

  const antiDetection = normalizePurAntiDetection(mi);
  const speed = clamp(antiDetection.speed || 1, 0.5, 2);
  const zooms = normalizePurZooms(body.zooms, body.cuts, fps);
  const clipFile = clipFiles[0] || '';
  const aspect = options.canvas || platformRules.aspect_ratio || '9:16';
  const canvas = PUR_CANVAS[aspect] || PUR_CANVAS['9:16'];

  const entry = {
    rank: 1,
    source_id: `pur_${pack.identite?.angle_id || pack.pack_id || 'clip'}`,
    clip_file: clipFile,
    duration_seconds: sourceDuration,
    start_frame: 0,
    role: 'pur_clip',
    anti_detection: antiDetection,
    zooms,
    sfx_list: normalizePurSfx(mi),
  };

  return {
    schema_version: 'dev10.pur.v1',
    mode: 'pur_pack',
    fps,
    canvas: { ...canvas, aspect },
    narrative: {
      category: style.pacing || '',
      energy_level: style.energy_level || 'high',
      overlay: buildPurOverlay(overlayLines, mainTitle, hookDuration, fps),
    },
    entries: [entry],
    rank_count: 1,
    final_rank: entry,
    duration_seconds: sourceDuration,
    total_frames: Math.max(1, Math.round((sourceDuration / speed) * fps)),
    pur: {
      pack_id: pack.pack_id || '',
      angle_id: pack.identite?.angle_id || '',
      generated_at: pack.generated_at || mi.metadata?.generated_at || '',
      generator: mi.metadata?.generator || 'F06_DIRECTOR',
      source: segment.source_url || segment.vod_url || '',
      start_sec: Number(segment.start_sec || 0),
      end_sec: Number(segment.end_sec || 0),
      platform: platformRules.platform || 'youtube_shorts',
      hook: {
        duration_sec: hookDuration,
        philosophy: hook.philosophy || '',
        zoom: hook.zoom || {},
      },
      body: { duration_sec: bodyDuration, energy_curve: body.energy_curve || [] },
      outro: { duration_sec: outroDuration, type: outro.type || 'fade_to_black', note: outro.note || '' },
      compliance: mi.compliance || pack.compliance || {},
    },
  };
}

/**
 * Extrait les lignes d'overlay depuis le copywriting v2 (fallback text_payload).
 * overlay_title : "LIGNE 1\nLIGNE 2" → ['LIGNE 1', 'LIGNE 2']
 */
export function extractOverlayLines(copywriting = {}) {
  const raw = copywriting.overlay_title || copywriting.title || '';
  const lines = String(raw).split(/\n/).map((l) => l.trim()).filter(Boolean).slice(0, 3);
  if (lines.length > 0) return lines;
  const ost = copywriting.on_screen_text || '';
  if (ost) return String(ost).split(/\n/).map((l) => l.trim()).filter(Boolean).slice(0, 3);
  return [];
}

/**
 * Anti-detection réelle depuis le bloc anti_detection du pack PUR.
 * techniques[] : mirror, speed ("1.05x"), crop ("2.5%"), sfx_*.
 */
export function normalizePurAntiDetection(mi = {}) {
  const block = mi.anti_detection || {};
  const techniques = Array.isArray(block.techniques) ? block.techniques : [];
  const out = {
    mirror: false,
    speed: 1.0,
    breathing_zoom: { enabled: true, min_scale: 1.02, max_scale: 1.08, cycle_seconds: 8 },
    crop_pct: 0,
    principle: block.principle || '',
  };
  for (const t of techniques) {
    const name = String(t.name || '').toLowerCase();
    const optimal = String(t.optimal || t.action || '');
    if (name === 'mirror') out.mirror = true;
    else if (name === 'speed') {
      const m = optimal.match(/([0-9]+(?:\.[0-9]+)?)x/i);
      if (m) out.speed = Number(m[1]);
    } else if (name === 'crop') {
      const m = optimal.match(/([0-9]+(?:\.[0-9]+)?)\s*%/);
      if (m) out.crop_pct = Number(m[1]);
    }
  }
  return out;
}

/**
 * Zooms frame-exact depuis body.zooms (intensity_pct "108-115%",
 * duration_in "0.1s (2-3 frames a 30fps)", moment_sec).
 */
export function normalizePurZooms(zooms = [], cuts = [], fps = 30) {
  const list = Array.isArray(zooms) ? zooms : [];
  return list.map((z) => {
    const intensity = String(z.intensity_pct || '');
    const nums = intensity.match(/([0-9]+(?:\.[0-9]+)?)/g) || [];
    const from = nums.length > 0 ? Number(nums[0]) / 100 : 1.08;
    const to = nums.length > 1 ? Number(nums[1]) / 100 : from;
    const durMatch = String(z.duration_in || '').match(/([0-9]+(?:\.[0-9]+)?)\s*s/i);
    const seconds = durMatch ? Number(durMatch[1]) : 0.1;
    return {
      moment_sec: Number(z.moment_sec || 0),
      moment_frame: Math.round(Number(z.moment_sec || 0) * fps),
      type: z.type || 'zoom',
      scale_from: from,
      scale_to: to,
      frames: Math.max(1, Math.round(seconds * fps)),
      easing: z.easing || 'NONE',
      sfx_sync: z.sfx_sync || '',
    };
  });
}

/** SFX dérivés des zooms (sfx_sync) — volume 50-60% sous la voix. */
export function normalizePurSfx(mi = {}) {
  const body = mi.body || {};
  const zooms = Array.isArray(body.zooms) ? body.zooms : [];
  const list = [];
  for (const z of zooms) {
    const sync = String(z.sfx_sync || '');
    if (!sync) continue;
    const volMatch = sync.match(/([0-9]+(?:\.[0-9]+)?)\s*%/);
    const typeMatch = sync.match(/^(impact|whoosh|boom|riser|hit|sub_drop)/i);
    list.push({
      moment_frame: Math.round(Number(z.moment_sec || 0) * 30),
      type: typeMatch ? typeMatch[1].toLowerCase() : 'impact',
      volume: volMatch ? clamp(Number(volMatch[1]) / 100, 0.1, 1) : 0.55,
    });
  }
  return list;
}

function buildPurOverlay(lines, mainTitle = {}, hookDuration, fps) {
  return {
    lines,
    font: mainTitle.font || 'Montserrat ExtraBold / Bebas Neue (800-900)',
    fallback_font: mainTitle.fallback || 'Arial Black, Impact',
    color: mainTitle.color || '#FFFFFF',
    accent: mainTitle.accent || '#FFD700',
    outline: mainTitle.outline || '#000000',
    position: mainTitle.position || 'haut vers le centre',
    font_size: 68,
    animation: mainTitle.animation || 'pop_in',
    animation_frames: Math.max(2, Math.round(0.2 * fps)),
    visible_from_frame: Math.round(hookDuration * fps),
    visible: mainTitle.visible || 'toute la duree',
  };
}

function createEmptyPurManifest(fps) {
  return {
    schema_version: 'dev10.pur.v1',
    mode: 'pur_pack',
    fps,
    canvas: { ...PUR_CANVAS['9:16'], aspect: '9:16' },
    narrative: { category: '', energy_level: '', overlay: { lines: [] } },
    entries: [],
    rank_count: 0,
    final_rank: null,
    duration_seconds: 0,
    total_frames: 0,
    pur: {},
  };
}

export default parseMontageInstructions;
