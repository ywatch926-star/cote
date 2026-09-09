/* ═══════════════════════════════════════════════════════════════════
   PurPackComposition — Mode PUR côté RENDU (F04 PICTOR)
   Miroir exact du composant F03 Preview : mêmes calques, mêmes valeurs.
   Consomme codex.pur_manifest (dev10.pur.v1) + clips téléchargés par F00-PUR.
   ═══════════════════════════════════════════════════════════════════ */
import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig, Video } from 'remotion';
import { normalizePurManifest, purZoomAtFrame, purAntiTransform } from './purPackCompilation';

export function PurPackComposition({ purManifest: rawManifest }) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const manifest = normalizePurManifest(rawManifest, fps);
  const entry = manifest.entries?.[0] || {};
  const overlay = manifest.narrative?.overlay || {};
  const pur = manifest.pur || {};

  const videoUrl = entry.clip_file ? staticFile(entry.clip_file.replace(/^\.?\//, '')) : null;

  const anti = entry.anti_detection || {};
  const speed = Number(anti.speed || 1);
  const antiTransform = purAntiTransform(anti, frame, fps);
  const zoomScale = purZoomAtFrame(entry.zooms, frame);

  const overlayFrom = Number(overlay.visible_from_frame ?? Math.round(3 * fps));
  const popFrames = Number(overlay.animation_frames ?? 6);
  const popProgress = Math.min(1, (frame - overlayFrom) / Math.max(1, popFrames));
  const overlayVisible = frame >= overlayFrom && overlay.lines?.length > 0;
  const popScale = overlayVisible ? (0.9 + 0.2 * Math.min(1, popProgress) - 0.1 * Math.max(0, popProgress - 0.55)) : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', overflow: 'hidden' }}>
      {(entry.sfx_list || []).map((sfx, index) => (
        Math.abs(frame - Number(sfx.moment_frame || 0)) < 1 && sfx.type ? (
          <Sequence key={`pur_sfx_${index}`} from={Number(sfx.moment_frame || 0)} durationInFrames={Math.max(1, durationInFrames - Number(sfx.moment_frame || 0))}>
            <Audio src={staticFile(`sfx/${sfx.type}.mp3`)} volume={Number(sfx.volume ?? 0.55)} />
          </Sequence>
        ) : null
      ))}

      <AbsoluteFill style={{ transform: antiTransform, transformOrigin: 'center center' }}>
        {videoUrl ? (
          <Video
            src={videoUrl}
            startFrom={Math.round(frame * speed)}
            muted
            playbackRate={speed}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div style={{ color: '#ff8866', fontSize: 40, textAlign: 'center', alignSelf: 'center' }}>
            CLIP PUR MANQUANT — F00-PUR doit télécharger le segment
          </div>
        )}
      </AbsoluteFill>

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
