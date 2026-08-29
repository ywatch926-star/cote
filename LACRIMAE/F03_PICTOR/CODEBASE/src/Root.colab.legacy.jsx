/**
 * LACRIMAE — F03 PICTOR
 * Root Remotion — déclare la composition LacrimaeShort
 *
 * IMPORTANT — FIX CRITIQUE :
 * Ce fichier est un TEMPLATE. Il sera réécrit par LAC_F03.ipynb avant le rendu
 * avec les vrais chemins vers timing.json, creative_config.json, images et audio.
 *
 * Ne jamais lancer 'npx remotion render' sans que le notebook ait d'abord
 * exécuté l'étape "Préparer Root.jsx" qui injecte les vraies données.
 *
 * Données de placeholder utilisées ici pour permettre l'ouverture du Studio
 * Remotion sans erreur de compilation.
 */

import { Composition } from "remotion";
import { LacrimaeShort } from "./components/LacrimaeShort";

// Résolution vidéo : 1080x1920 (9:16 vertical)
const WIDTH  = 1080;
const HEIGHT = 1920;

// ── Placeholder timing ────────────────────────────────────────────────────────
// Remplacé par les vraies valeurs issues de timing.json via le notebook
const PLACEHOLDER_TIMING = {
  audio_duration_s: 30,
  total_frames: 900,
  fps: 30,
  words: [
    { word: "LACRIMAE", start_s: 0, end_s: 1, start_frame: 0, end_frame: 30, is_strong: true },
  ],
};

// Ces valeurs seront écrasées par le notebook lors de la préparation du rendu
const FPS          = PLACEHOLDER_TIMING.fps;
const TOTAL_FRAMES = PLACEHOLDER_TIMING.total_frames;

export const LacrimaeRoot = () => {
  return (
    <Composition
      id="LacrimaeShort"
      component={LacrimaeShort}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={{
        timing:   PLACEHOLDER_TIMING,
        config:   null,   // injecté par le notebook (creative_config.json)
        images:   [],     // injecté par le notebook (require() de chaque image)
        audioSrc: null,   // injecté par le notebook (chemin audio_clean.mp3)
      }}
    />
  );
};
