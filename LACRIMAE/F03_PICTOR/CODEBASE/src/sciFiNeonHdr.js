function clampIntensity(intensity) {
  return Math.max(0, Math.min(100, Number(intensity) || 0)) / 100;
}

export function sciFiNeonHdrFilter(intensity = 0) {
  const amount = clampIntensity(intensity);
  if (amount <= 0) return '';
  const contrast = (1 + 0.35 * amount).toFixed(3);
  const saturation = (1 + 0.95 * amount).toFixed(3);
  const brightness = (1 - 0.03 * amount).toFixed(3);
  const hueRotate = (4 * amount).toFixed(2);
  return `contrast(${contrast}) saturate(${saturation}) brightness(${brightness}) hue-rotate(${hueRotate}deg)`;
}

export function sciFiNeonHdrOverlayStyle(intensity = 0) {
  const amount = clampIntensity(intensity);
  if (amount <= 0) return null;
  return {
    background: 'radial-gradient(circle at 18% 28%, rgba(0,255,90,0.16), transparent 18%), radial-gradient(circle at 82% 35%, rgba(0,220,255,0.18), transparent 24%), radial-gradient(circle at 55% 78%, rgba(255,65,0,0.14), transparent 22%), radial-gradient(circle at 72% 58%, rgba(255,0,80,0.09), transparent 16%)',
    opacity: (0.48 * amount).toFixed(3),
    mixBlendMode: 'screen',
    pointerEvents: 'none',
  };
}
