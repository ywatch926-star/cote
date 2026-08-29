import React from 'react';
import { Composition } from 'remotion';
import { OmniComposition } from '../preview/OmniComposition';
import codex from '../../public/codex.json';
import sequences from '../../public/sequences.json';
import { getCompositionConfig } from '../preview/compositionConfig';

const clip = codex.clips?.[0] || codex;
const video = clip.video || {};
  const { fps = 30, total_frames = 300 } = video;
  const composition = getCompositionConfig(codex, codex.session || {});
  const previewFrames = Number(sequences.total_frames || total_frames);

export const RemotionRoot = () => {
  return (
    <Composition
      id="LacrimaeShort"
      component={OmniComposition}
      durationInFrames={previewFrames}
      fps={fps}
      width={composition.width}
      height={composition.height}
      defaultProps={{
        codex: clip,
        session: codex.session || {},
        videoSrc: './' + (video.source || sequences.source || 'clip_001.mp4'),
        sequences,
      }}
    />
  );
};
