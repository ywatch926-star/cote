import React from 'react';
import { Composition, staticFile } from 'remotion';
import { OmniComposition } from './OmniComposition';
import codex from './data/codex.json';
import sequences from './data/sequences.json';
import hybridManifest from './data/hybrid_manifest.json';
import musicTimeline from './data/music_timeline.json';
import { getCompositionConfig } from './compositionConfig';
import { normalizeRevealManifest } from './revealCompilation';
import { normalizeRankingManifest } from './rankingCompilation';
import { normalizePurManifest } from './purPackCompilation';
import revealSources from './data/reveal_sources.json';
import rankingSources from './data/ranking_manifest.json';
import purSources from './data/pur_manifest.json';

const clip = codex.clips?.[0] || codex;
const video = clip.video || {};
const fps = Number(sequences.fps || video.fps || 30);
const hybridActive = codex.session?.review_mode === 'hybrid_narrative' && hybridManifest.mode === 'hybrid_narrative';
const revealActive = codex.session?.review_mode === 'reveal_compilation';
const rankingActive = codex.session?.review_mode === 'ranking_compilation';
const purActive = codex.session?.review_mode === 'pur_pack';
const revealManifest = revealActive
  ? normalizeRevealManifest(codex.reveal_manifest || codex.session?.reveal || revealSources, fps, Number(sequences.total_frames || video.total_frames || 300))
  : null;
const rankingManifest = rankingActive
  ? normalizeRankingManifest(codex.ranking_manifest || codex.session?.ranking || rankingSources, fps, Number(sequences.total_frames || video.total_frames || 300))
  : null;
const purManifest = purActive
  ? normalizePurManifest(codex.pur_manifest || codex.session?.pur_manifest || purSources, fps)
  : null;
const durationInFrames = purManifest?.total_frames || rankingManifest?.total_frames || revealManifest?.total_frames || (hybridActive
  ? Number(hybridManifest.total_frames || sequences.total_frames || video.total_frames || 300)
  : Number(sequences.total_frames || video.total_frames || 300));
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
      hybridManifest: hybridActive ? hybridManifest : null,
      videoSrc: staticFile(video.source || sequences.source || 'video_source.mp4'),
      musicTimeline,
      revealManifest: rankingManifest || revealManifest,
      purManifest: purActive ? purManifest : null,
    }}
  />
);
