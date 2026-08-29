import React from 'react';
import { Composition, staticFile } from 'remotion';
import { OmniComposition } from './OmniComposition';
import codex from './data/codex.json';
import sequences from './data/sequences.json';
import { getCompositionConfig } from './compositionConfig';

const clip = codex.clips?.[0] || codex;
const video = clip.video || {};
const fps = Number(sequences.fps || video.fps || 30);
const durationInFrames = Number(sequences.total_frames || video.total_frames || 300);
const composition = getCompositionConfig(codex, codex.session || {});
const width = composition.width;
const height = composition.height;

export const LacrimaeRoot = () => (
  <Composition
    id="LacrimaeShort"
    component={OmniComposition}
    durationInFrames={durationInFrames}
    fps={fps}
    width={width}
    height={height}
    defaultProps={{
      codex: clip,
      session: codex.session || {},
      sequences,
      videoSrc: staticFile(video.source || sequences.source || 'video_source.mp4'),
    }}
  />
);
