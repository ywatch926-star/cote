/**
 * LACRIMAE — F03 PICTOR
 * Composant principal — rendu frame par frame du Short
 *
 * Inputs attendus (via props) :
 *   - timing       : timing.json (mots, frames, durée)
 *   - config       : creative_config.json (fonts, grain, filtres, cut)
 *   - images       : tableau de chemins d'images (require statique)
 *   - audioSrc     : chemin vers audio_clean.mp3
 */

import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  Audio,
  Img,
  AbsoluteFill,
  interpolate,
  Easing,
} from "remotion";
import { loadFont as loadCinzel } from "@remotion/google-fonts/Cinzel";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";

// Charger les fonts Google Remotion
const { fontFamily: cinzel }    = loadCinzel();
const { fontFamily: playfair }  = loadPlayfair();

// ─── COMPOSANT PRINCIPAL ──────────────────────────────────────────────────────

export const LacrimaeShort = ({ timing, config, images = [], audioSrc = null }) => {
  // FIX CRITICAL: images et audioSrc ont des valeurs par défaut
  // pour éviter les TypeError si les props ne sont pas passées par Root.jsx
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Config par défaut si non fournie
  const cfg = config || {
    cut_interval_frames: 7,
    image_order: "sequential",
    grain_overlay_opacity: 0.30,
    css_filters: "contrast(1.2) brightness(0.88) sepia(0.15)",
    blend_mode: "screen",
    word_animation: "fade",
    letter_spacing: "0.12em",
    text_shadow: "0px 4px 12px rgba(0,0,0,0.9)",
  };

  // ── Sélection de l'image au frame courant ──────────────────────────────────
  const cutInterval = cfg.cut_interval_frames || 7;
  // FIX: images.length sécurisé — images=[] par défaut évite le crash
  const imgIdx = images.length > 0
    ? Math.floor(frame / cutInterval) % images.length
    : 0;
  const currentImage = images.length > 0 ? images[imgIdx] : null;

  // ── Mot courant ────────────────────────────────────────────────────────────
  const currentWord = getCurrentWord(timing.words, frame);

  // ── Filtres CSS ────────────────────────────────────────────────────────────
  const bgFilter = cfg.css_filters || "contrast(1.2) brightness(0.88) sepia(0.15)";

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>

      {/* Audio */}
      {audioSrc && (
        <Audio src={audioSrc} />
      )}

      {/* Image de fond */}
      {currentImage && (
        <ImageBackground
          src={currentImage}
          filter={bgFilter}
          frame={frame}
          cutInterval={cutInterval}
          imgIdx={imgIdx}
        />
      )}

      {/* Overlay assombrissant */}
      <AbsoluteFill
        style={{
          background: "linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.5) 100%)",
        }}
      />

      {/* Film grain — animé frame par frame */}
      <GrainOverlay opacity={cfg.grain_overlay_opacity} frame={frame} />

      {/* Sous-titres */}
      {currentWord && (
        <SubtitleLayer
          word={currentWord}
          frame={frame}
          config={cfg}
          cinzel={cinzel}
          playfair={playfair}
        />
      )}

    </AbsoluteFill>
  );
};


// ─── IMAGE BACKGROUND ─────────────────────────────────────────────────────────

const ImageBackground = ({ src, filter, frame, cutInterval, imgIdx }) => {
  // Micro-zoom scale(1.02) à l'apparition de chaque nouvelle image
  const frameInCut = frame % cutInterval;
  const zoom = interpolate(frameInCut, [0, cutInterval], [1.02, 1.0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  return (
    <AbsoluteFill
      style={{
        filter,
        transform: `scale(${zoom})`,
        transformOrigin: "center center",
      }}
    >
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: "center",
        }}
      />
    </AbsoluteFill>
  );
};


// ─── GRAIN OVERLAY ────────────────────────────────────────────────────────────

const GrainOverlay = ({ opacity, frame }) => {
  // FIX: grain animé — baseFrequency varie légèrement selon le frame
  // pour un effet organique plutôt que figé
  const baseFreq = (0.82 + (frame % 17) * 0.003).toFixed(4);
  const numOctaves = 3 + (frame % 3);
  const svgGrain = `data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='${baseFreq}' numOctaves='${numOctaves}' seed='${frame % 99}' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E`;

  return (
    <AbsoluteFill
      style={{
        backgroundImage: `url("${svgGrain}")`,
        backgroundSize: "512px 512px",
        opacity: opacity || 0.30,
        mixBlendMode: "screen",
        pointerEvents: "none",
      }}
    />
  );
};


// ─── SUBTITLE LAYER ───────────────────────────────────────────────────────────

const SubtitleLayer = ({ word, frame, config, cinzel, playfair }) => {
  // Fade-in mot par mot
  const wordAge = frame - word.start_frame;
  const fadeDuration = Math.min(6, word.end_frame - word.start_frame);
  const opacity = interpolate(wordAge, [0, fadeDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });

  const isStrong = word.is_strong;
  const fontFamily = isStrong ? playfair : cinzel;
  const fontSize = isStrong ? 72 : 62;
  const fontStyle = isStrong ? "italic" : "normal";
  const fontWeight = isStrong ? 700 : 400;
  const color = isStrong ? "#e8c96a" : "#ffffff";

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 180,
      }}
    >
      <div
        style={{
          fontFamily,
          fontSize,
          fontStyle,
          fontWeight,
          color,
          opacity,
          letterSpacing: config.letter_spacing || "0.12em",
          textShadow: config.text_shadow || "0px 4px 12px rgba(0,0,0,0.9)",
          textAlign: "center",
          padding: "0 80px",
          lineHeight: 1.2,
          userSelect: "none",
        }}
      >
        {word.word}
      </div>
    </AbsoluteFill>
  );
};


// ─── HELPERS ──────────────────────────────────────────────────────────────────

/**
 * Retourne le mot actif au frame donné.
 * Retourne null entre deux mots (silence).
 */
function getCurrentWord(words, frame) {
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    if (frame >= w.start_frame && frame < w.end_frame) {
      return w;
    }
  }
  return null;
}
