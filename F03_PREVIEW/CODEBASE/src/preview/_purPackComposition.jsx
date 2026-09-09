/* ═══════════════════════════════════════════════════════════════════
   PurPackComposition — Mode PUR (packs PERTURABO → dev10.pur.v1)

   Consomme le manifeste produit par parsePurPack() (bridgeClipper.js) :
     - clip plein écran (fit cover)
     - hook 0-3s : visage speaker, PAS de texte, zoom brutal_impact
     - overlay titre 2 lignes après le hook (copywriting v2)
     - zooms frame-exacts depuis body.zooms
     - anti-détection : mirror + speed + breathing zoom + crop
   ═══════════════════════════════════════════════════════════════════ */
import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig, Video } from 'remotion';
import { antiDetectionTransform, antiDetectionSpeed } from './antiDetection';

/** Zoom ponctuel actif à ce frame ? → scale multipliant. */
function purZoomAtFrame(zooms, frame) {
  let scale = 1;
  for (const z of zooms || []) {
    const start = Number(z.moment_frame || 0);
    const end = start + Number(z.frames || 3);
    if (frame >= start && frame < end) {
      const p = (frame - start) / Math.max(1, end - start);
      // brutal_impact : pic immédiat puis retour (in 0.1s, out immédiat)
      scale *= z.easing === 'NONE' ? z.scale_to : (z.scale_from + (z.scale_to - z.scale_from) * p);
    }
  }
  return scale;
}

/** Crop offset depuis anti_detection.crop_pct (2.5% des bords). */
function purCropTransform(cropPct) {
  if (!cropPct) return '';
  const s = 1 + 2 * (cropPct / 100);
  return `scale(${s.toFixed(4)})`;
}

export function PurPackComposition({ purManifest, session: sessionProp }) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const manifest = purManifest || sessionProp?.pur || {};
  const entry = manifest.entries?.[0] || {};
  const overlay = manifest.narrative?.overlay || {};
  const pur = manifest.pur || {};

  const localFrame = frame;
  const videoUrl = entry.clip_file ? entry.clip_file.replace(/^\.?\//, '') : null;

  // Anti-detection
  const anti = entry.anti_detection || {};
  const speed = Number(anti.speed || 1);
  const antiTransform = [antiDetectionTransform(anti, frame, fps), purCropTransform(anti.crop_pct)]
    .filter(Boolean).join(' ');

  // Zooms ponctuels (brutal_impact / snap_zoom)
  const zoomScale = purZoomAtFrame(entry.zooms, localFrame);

  // Overlay visible après le hook
  const overlayFrom = Number(overlay.visible_from_frame ?? Math.round(3 * fps));
  const popFrames = Number(overlay.animation_frames ?? 6);
  const popProgress = Math.min(1, (frame - overlayFrom) / Math.max(1, popFrames));
  const overlayVisible = frame >= overlayFrom && overlay.lines?.length > 0;
  const popScale = overlayVisible ? (0.9 + 0.2 * Math.min(1, popProgress) - 0.1 * Math.max(0, popProgress - 0.55)) : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', overflow: 'hidden' }}>
      {/* SFX des zooms (volume 50-60% sous la voix) */}
      {(entry.sfx_list || []).map((sfx, index) => (
        Math.abs(frame - Number(sfx.moment_frame || 0)) < 1 && sfx.type ? (
          <Sequence key={`pur_sfx_${index}`} from={Number(sfx.moment_frame || 0)} durationInFrames={Math.max(1, durationInFrames - Number(sfx.moment_frame || 0))}>
            <Audio src={staticFile(`sfx/${sfx.type}.mp3`)} volume={Number(sfx.volume ?? 0.55)} />
          </Sequence>
        ) : null
      ))}

      <AbsoluteFill
        style={{
          transform: [antiTransform, `scale(${zoomScale.toFixed(4)})`].filter((t) => !t.includes('scale(1)') || t !== 'scale(1.0000)').join(' '),
          transformOrigin: 'center center',
        }}
      >
        {videoUrl ? (
          <Video
            src={videoUrl}
            startFrom={Math.round(localFrame * speed)}
            muted
            playbackRate={speed}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div style={{ color: '#ff8866', fontSize: 40, textAlign: 'center', alignSelf: 'center' }}>
            CLIP PUR MANQUANT — lance F00-PUR (f00_pur.py)
          </div>
        )}
      </AbsoluteFill>

      {/* Overlay titre PUR : APRÈS le hook (jamais pendant 0-3s) */}
      {overlayVisible && (
        <AbsoluteFill style={{ pointerEvents: 'none' }}>
          <div
            style={{
              position: 'absolute',
              left: '6%',
              right: '6%',
              top: '22%',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
              transform: `scale(${popScale.toFixed(3)})`,
              transformOrigin: 'center top',
            }}
          >
            {overlay.lines.map((line, index) => (
              <div
                key={`pur_line_${index}`}
                style={{
                  fontFamily: `${overlay.fallback_font || 'Arial Black, Impact'}, sans-serif`,
                  fontSize: Number(overlay.font_size || 68),
                  fontWeight: 900,
                  lineHeight: 1.04,
                  textTransform: 'uppercase',
                  color: index === 0 ? (overlay.color || '#FFFFFF') : (overlay.accent || '#FFD700'),
                  WebkitTextStroke: `3px ${overlay.outline || '#000000'}`,
                  textShadow: '0 4px 18px rgba(0,0,0,0.85)',
                }}
              >
                {line}
              </div>
            ))}
          </div>
        </AbsoluteFill>
      )}

      {/* Outro : fade_to_black final */}
      {pur.outro?.type === 'fade_to_black' && (() => {
        const outroFrames = Math.round(Number(pur.outro.duration_sec || 1) * fps);
        const outroStart = durationInFrames - outroFrames;
        if (frame < outroStart) return null;
        const p = (frame - outroStart) / Math.max(1, outroFrames);
        return <AbsoluteFill style={{ background: `rgba(0,0,0,${(p * 0.95).toFixed(3)})`, pointerEvents: 'none' }} />;
      })()}
    </AbsoluteFill>
  );
}

export default PurPackComposition;
