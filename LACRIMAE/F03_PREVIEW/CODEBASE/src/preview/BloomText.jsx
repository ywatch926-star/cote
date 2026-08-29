import React, { useMemo, useRef } from 'react';
import { useCurrentFrame, interpolate } from 'remotion';

/* ──────────────────────────────────────────────────────────────
 * BloomText — Texte avec bloom SVG + 3D CSS
 * Remplace les 7 couches textShadow par un vrai bloom SVG (feGaussianBlur)
 * Remplace le fake 3D par CSS perspective + translateZ
 *
 * Props:
 *   overlay: object — l'entrée text_overlays du codex
 *   frame: number
 *   fps: number
 * ────────────────────────────────────────────────────────────── */

export const BloomText = ({ overlay, frame, fps }) => {
  const {
    content,
    animation = 'word_by_word',
    font = 'Impact, Arial Black, sans-serif',
    size = 96,
    color = '#FFFFFF',
    stroke_color = '#FFFFFF',
    stroke_width = 1,
    shadow = '2px 4px 8px rgba(0,0,0,0.5)',
    position = 'center',
    letter_spacing = '0em',
    glow_intensity = 35,
    depth_3d = 1,
    start_frame = 0,
    end_frame = 300,
  } = overlay;

  const localFrame = frame - start_frame;
  const words = content.split(' ');

  // Timing mot par mot
  const totalDuration = end_frame - start_frame;
  const wordFadeFrames = 8;
  const revealDuration = Math.max(totalDuration * 0.6, words.length * 8);
  const wordsPerFrame =
    animation === 'word_by_word' ? revealDuration / words.length : 0;

  // Intensité du bloom (stdDeviation du flou gaussien)
  const bloomStdDev = (glow_intensity / 100) * 4; // 0 à 4px de flou

  // Profondeur 3D (translateZ en px)
  const zDepth = depth_3d * 15; // 0 à 150px de profondeur

  // ID unique pour le filtre SVG (évite les collisions)
  const filterId = useMemo(
    () => `bloom-${overlay.id || Math.random().toString(36).substr(2, 9)}`,
    [overlay.id]
  );

  // Animation du bloc entier
  let blockOpacity = 1;
  let blockScale = 1;

  if (animation === 'pop') {
    blockOpacity = interpolate(localFrame, [0, 6], [0, 1], {
      extrapolateRight: 'clamp',
    });
    blockScale = interpolate(localFrame, [0, 6], [0.8, 1], {
      extrapolateRight: 'clamp',
    });
  } else if (animation === 'fade_in') {
    blockOpacity = interpolate(localFrame, [0, 15], [0, 1], {
      extrapolateRight: 'clamp',
    });
  } else if (animation === 'fade_in_slow') {
    blockOpacity = interpolate(localFrame, [0, 30], [0, 1], {
      extrapolateRight: 'clamp',
    });
  }

  // Style de base du texte
  const baseTextStyle = {
    fontFamily: font,
    fontSize: `${size}px`,
    color: color,
    WebkitTextStroke:
      stroke_width > 0 ? `${stroke_width}px ${stroke_color}` : '0px transparent',
    letterSpacing: letter_spacing,
    fontWeight: 900,
    textTransform: 'uppercase',
    lineHeight: 1.1,
    textAlign: 'center',
    pointerEvents: 'none',
    display: 'inline',
    whiteSpace: 'pre-wrap',
    wordWrap: 'break-word',
    maxWidth: '85%',
    filter: glow_intensity > 0 ? `url(#${filterId})` : 'none',
    textShadow: shadow,
  };

  // Container avec perspective 3D
  const container3DStyle = {
    perspective: '800px',
    perspectiveOrigin: 'center center',
  };

  // Inner avec transform 3D
  const inner3DStyle = {
    transform: `translateZ(${zDepth}px) rotateX(${depth_3d > 0 ? 3 : 0}deg)`,
    transformStyle: 'preserve-3d',
  };

  // Position
  const positionStyle = getPositionStyle(position);

  // SVG bloom filter (hidden, juste pour définir le filtre)
  const bloomFilter = (
    <svg
      style={{
        position: 'absolute',
        width: 0,
        height: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
    >
      <defs>
        <filter id={filterId} x="-50%" y="-50%" width="200%" height="200%">
          {/* Couche de flou pour le bloom */}
          <feGaussianBlur
            in="SourceGraphic"
            stdDeviation={bloomStdDev}
            result="blur1"
          />
          {/* Deuxième couche de flou plus large pour le halo */}
          <feGaussianBlur
            in="SourceGraphic"
            stdDeviation={bloomStdDev * 2.5}
            result="blur2"
          />
          {/* Couleur du bloom = couleur du texte */}
          <feFlood floodColor={color} floodOpacity="0.6" result="floodColor" />
          <feComposite in="floodColor" in2="blur2" operator="in" result="coloredBlur" />
          {/* Merge: blur large + blur moyen + texte net */}
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="blur1" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
    </svg>
  );

  // Rendu mot par mot
  if (animation === 'word_by_word') {
    return (
      <>
        {bloomFilter}
        <div
          style={{
            ...positionStyle,
            ...container3DStyle,
            pointerEvents: 'none',
            zIndex: 10,
          }}
        >
          <div
            style={{
              ...inner3DStyle,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{ ...baseTextStyle, opacity: 1, transform: 'none' }}>
              {words.map((word, i) => {
                const wordStartFrame = i * wordsPerFrame;
                const wordLocalFrame = localFrame - wordStartFrame;
                const wordOpacity = interpolate(
                  wordLocalFrame,
                  [0, wordFadeFrames],
                  [0, 1],
                  { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
                );
                const wordScale = interpolate(
                  wordLocalFrame,
                  [0, wordFadeFrames],
                  [0.92, 1],
                  { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
                );

                return (
                  <React.Fragment key={i}>
                    <span
                      style={{
                        display: 'inline-block',
                        opacity: wordOpacity,
                        transform: `scale(${wordScale})`,
                        transition: 'none',
                      }}
                    >
                      {word}
                    </span>
                    {i < words.length - 1 ? '\u00A0' : ''}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        </div>
      </>
    );
  }

  // Animations bloc entier (pop, fade_in, fade_in_slow)
  return (
    <>
      {bloomFilter}
      <div
        style={{
          ...positionStyle,
          ...container3DStyle,
          pointerEvents: 'none',
          zIndex: 10,
        }}
      >
        <div
          style={{
            ...inner3DStyle,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              ...baseTextStyle,
              opacity: blockOpacity,
              transform: `scale(${blockScale})`,
            }}
          >
            {content}
          </div>
        </div>
      </div>
    </>
  );
};

/* ──────────────────────────────────────────────────────────────
 * Helper: Position styles
 * ────────────────────────────────────────────────────────────── */

function getPositionStyle(position) {
  switch (position) {
    case 'center':
      return {
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '90%',
      };
    case 'top':
      return {
        position: 'absolute',
        top: '10%',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '90%',
      };
    case 'center_bottom':
      return {
        position: 'absolute',
        bottom: '15%',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '90%',
      };
    case 'bottom':
      return {
        position: 'absolute',
        bottom: '8%',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '90%',
      };
    case 'center_left':
      return {
        position: 'absolute',
        top: '45%',
        left: '10%',
        width: '80%',
      };
    default:
      return {
        position: 'absolute',
        bottom: '15%',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '90%',
      };
  }
}
