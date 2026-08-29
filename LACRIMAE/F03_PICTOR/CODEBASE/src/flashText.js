export function normalizeFlashTextUnits(texts = {}) {
  const source = Array.isArray(texts.units) && texts.units.length
    ? texts.units
    : String(texts.content || '').trim().split(/\s+/).filter(Boolean).map((text) => ({ text }));
  let cursor = 0;
  return source.map((unit, index) => {
    const duration = Math.max(1, Number(unit.duration_frames) || 8);
    const explicitStart = index > 0 && Number(unit.start_frame) > 0 ? Number(unit.start_frame) : cursor;
    const normalized = {
      ...unit,
      id: unit.id || `word_${String(index + 1).padStart(3, '0')}`,
      text: String(unit.text || '').toUpperCase(),
      start_frame: explicitStart,
      duration_frames: duration,
      impact: Boolean(unit.impact),
      rotation_deg: Number(unit.rotation_deg) || 0,
      scale: Math.max(1, Math.min(10, Number(unit.scale) || 1)),
      blur_frames: Math.max(0, Math.min(3, Number(unit.blur_frames) || 0)),
    };
    cursor = explicitStart + duration;
    return normalized;
  });
}

export function activeFlashTextUnit(texts, frame) {
  return normalizeFlashTextUnits(texts).find((unit) => frame >= unit.start_frame && frame < unit.start_frame + unit.duration_frames) || null;
}

export function flashTextStyle(unit, frame, style = {}) {
  if (!unit) return null;
  const localFrame = frame - unit.start_frame;
  const blur = localFrame < unit.blur_frames ? Math.max(0.5, (unit.blur_frames - localFrame) * 1.5) : 0;
  return {
    position: 'absolute', top: '50%', left: '50%', width: '92%',
    transform: `translate(-50%, -50%) rotate(${unit.rotation_deg}deg) scale(${unit.scale})`,
    transformOrigin: 'center center',
    fontFamily: unit.font_family || style.font || 'Arial Black, Impact, sans-serif',
    fontSize: `${unit.font_size || style.size_title || 96}px`, fontWeight: 900, lineHeight: 0.95,
    letterSpacing: unit.letter_spacing || '-0.02em', textAlign: 'center', textTransform: 'uppercase',
    color: unit.impact ? (unit.impact_color || '#FF0000') : (unit.normal_color || '#FFFFFF'),
    WebkitTextStroke: `${unit.stroke_width ?? style.stroke_width ?? 0}px ${unit.stroke_color || style.stroke_color || '#000000'}`,
    textShadow: style.shadow || 'none', filter: blur ? `blur(${blur.toFixed(2)}px)` : 'none',
    whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', pointerEvents: 'none',
  };
}
