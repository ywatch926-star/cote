export const COMPOSITION_PRESETS = {
  vertical: { width: 1080, height: 1920, label: 'Vertical 9:16' },
  horizontal: { width: 1920, height: 1080, label: 'Horizontal 16:9' },
  square: { width: 1080, height: 1080, label: 'Carré 1:1' },
};

export const DEFAULT_COMPOSITION = {
  preset: 'vertical',
  width: 1080,
  height: 1920,
  fit: 'cover',
  background_fill: 'blurred_video',
  rotation_mode: 'none',
  rotation_step_deg: 1,
  rotation_total_deg: 360,
  rotation_direction: 1,
  rotation_layer: 'video',
};

export function getCompositionConfig(codex = {}, session = {}) {
  const raw = session.composition || codex.composition || {};
  const preset = raw.preset && COMPOSITION_PRESETS[raw.preset] ? raw.preset : 'vertical';
  const base = COMPOSITION_PRESETS[preset];
  return {
    ...DEFAULT_COMPOSITION,
    ...base,
    ...raw,
    width: Number(raw.width || base.width),
    height: Number(raw.height || base.height),
    rotation_step_deg: Number(raw.rotation_step_deg ?? 1),
    rotation_total_deg: Number(raw.rotation_total_deg ?? 360),
    rotation_direction: Number(raw.rotation_direction ?? 1) >= 0 ? 1 : -1,
  };
}

export function rotationForSequence(config, sequenceIndex, frame, fps = 30, durationInFrames = 300) {
  if (config.rotation_mode === 'per_sequence') {
    return sequenceIndex * config.rotation_step_deg * config.rotation_direction;
  }
  if (config.rotation_mode === 'continuous') {
    const progress = Math.min(1, Math.max(0, frame / Math.max(1, durationInFrames - 1)));
    return progress * config.rotation_total_deg * config.rotation_direction;
  }
  return 0;
}
