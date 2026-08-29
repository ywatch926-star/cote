export const DARK_LUXURY_NOIR_DEFAULTS = {
  enabled: false,
  intensity: 0,
};

export function darkLuxuryNoirFilter(intensity = 0) {
  const amount = Math.max(0, Math.min(100, Number(intensity) || 0)) / 100;
  if (amount <= 0) return '';
  const grayscale = (0.86 * amount).toFixed(3);
  const sepia = (0.34 * amount).toFixed(3);
  const saturation = (1 - 0.68 * amount).toFixed(3);
  const contrast = (1 + 0.42 * amount).toFixed(3);
  const brightness = (1 - 0.08 * amount).toFixed(3);
  return `grayscale(${grayscale}) sepia(${sepia}) saturate(${saturation}) contrast(${contrast}) brightness(${brightness})`;
}

export function darkLuxuryNoirOverlayStyle(intensity = 0) {
  const amount = Math.max(0, Math.min(100, Number(intensity) || 0)) / 100;
  if (amount <= 0) return null;
  return {
    background: 'radial-gradient(circle at 72% 28%, rgba(197,160,89,0.22), transparent 25%), radial-gradient(circle at 18% 68%, rgba(255,20,70,0.10), transparent 18%), radial-gradient(circle at 82% 70%, rgba(145,35,255,0.12), transparent 20%)',
    opacity: (0.55 * amount).toFixed(3),
    mixBlendMode: 'screen',
    pointerEvents: 'none',
  };
}
