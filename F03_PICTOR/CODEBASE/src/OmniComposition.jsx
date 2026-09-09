import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Video,
  Sequence,
  staticFile,
} from 'remotion';
import { normalizeSequences } from './virtualSequences';
import { getCompositionConfig, rotationForSequence } from './compositionConfig';
import { darkLuxuryNoirFilter, darkLuxuryNoirOverlayStyle } from './darkLuxuryNoir';
import { sciFiNeonHdrFilter, sciFiNeonHdrOverlayStyle } from './sciFiNeonHdr';
import { activeFlashTextUnit, flashTextStyle } from './flashText';
import { hybridTimelineFrame, hybridEgoStyle, hybridTextStyle } from './hybridNarrative';
import { normalizeMusicTimeline, buildAudioSegments } from './audioTimeline';
import { normalizeRevealManifest, revealSceneAtFrame, revealSourceForScene, revealMotionTransform } from './revealCompilation';
import { normalizeRankingManifest, rankingEntryAtFrame, rankingActiveRows, rankingMotionTransform } from './rankingCompilation';
import { PurPackComposition } from './_purPackComposition';

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
 * OmniComposition (F03 PREVIEW) â€” mÃªmes 6 calques que F04 RENDER :
 *   L1 BACKGROUND â†’ L2 CLIP â†’ L3 TITRE â†’ L4 PARAGRAPHE â†’ L5 LOGO â†’ L6 PRESETS
 * Props: codex (clip), videoSrc, session (bloc session v4)
 * â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */

const SESSION_FALLBACK = {
  background: { image: null, color: '#0a0a0a', scale: 1.0 },
  logo: { src: 'logo.png', width_pct: 20, position: 'bottom_left', opacity: 1.0 },
  texts_style: {
    font: 'Impact, Arial Black, sans-serif',
    size_title: 96,
    size_paragraph: 44,
    color: '#FFFFFF',
    stroke_color: '#000000',
    stroke_width: 4,
    shadow: '2px 4px 8px rgba(0,0,0,0.9)',
    glow_intensity: 0,
    letter_spacing: '0em',
    title_box: {
      enabled: false,
      color: 'rgba(0,0,0,0.7)',
      text_color: '#FFFFFF',
      border_color: '#FFFFFF',
      border_width: 0,
      radius: 12,
      padding: 12,
    },
    paragraph_box: {
      enabled: false,
      color: 'rgba(0,0,0,0.7)',
      text_color: '#FFFFFF',
      border_color: '#FFFFFF',
      border_width: 0,
      radius: 12,
      padding: 12,
    },
  },
  presets: {
    color_preset: 'punchy',
    color_css_filter: 'contrast(1.3) saturate(1.5) brightness(1.1)',
    contrast: 1.3,
    brightness: 1.1,
    enhance_4k: false,
    sharpening: 0,
    denoising: 0,
    vignette: 0.25,
    grain_intensity: 0.15,
  },
};

function RankingCompilationComposition({ session: sessionProp, rankingManifest, musicTimeline }) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const session = sessionProp || {};
  const manifest = normalizeRankingManifest(rankingManifest, fps, durationInFrames);
  const entry = rankingEntryAtFrame(manifest, frame);
  const music = normalizeMusicTimeline(musicTimeline || session.music || {}, fps, durationInFrames);
  const musicUrl = music.audio_src ? staticFile(music.audio_src.replace(/^\.\//, '')) : null;
  const audioSegments = musicUrl ? buildAudioSegments({ ...music, audio_src: musicUrl }, fps, durationInFrames) : [];
  const rows = rankingActiveRows(manifest, frame);
  const localFrame = Math.max(0, frame - Number(entry?.start_frame || 0));
  const videoUrl = entry?.clip_file ? staticFile(entry.clip_file.replace(/^\.\//, '')) : null;
  const final = entry?.role === 'final_rank' || entry?.rank === 1;
  const titleStyle = manifest.narrative?.title_style || {};
  const position = entry?.position || {};
  const transform = rankingMotionTransform(entry, frame, fps);
  const shake = final && localFrame < 12 ? Math.sin(localFrame * 2.8) * 18 * Math.pow(1 - localFrame / 12, 1.7) : 0;
  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', overflow: 'hidden', fontFamily: manifest.narrative?.font_family || 'Arial Black, sans-serif' }}>
      {musicUrl && audioSegments.map((segment, index) => <Sequence key={`ranking_music_${index}`} from={segment.from} durationInFrames={segment.duration}><Audio src={musicUrl} startFrom={segment.startFrom} volume={segment.volume} /></Sequence>)}
      {entry?.sfx?.enabled && entry.sfx.file && <Sequence from={Number(entry.start_frame || 0)} durationInFrames={Math.max(1, durationInFrames - Number(entry.start_frame || 0))}><Audio src={staticFile(entry.sfx.file.replace(/^\.\//, ''))} volume={Number(entry.sfx.volume ?? 1)} /></Sequence>}
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
        {videoUrl ? <Video src={videoUrl} startFrom={localFrame} muted style={{ position: 'absolute', left: `${position.x_pct ?? 50}%`, top: `${position.y_pct ?? 50}%`, width: `${Math.min(200, Math.max(5, 100 * (position.scale ?? 1)))}%`, height: 'auto', transform: `${transform} translateY(${shake.toFixed(2)}px)`, transformOrigin: 'center center', objectFit: 'contain' }} /> : <div style={{ color: '#ff8866', fontSize: 42 }}>CLIP MANQUANT</div>}
      </AbsoluteFill>
      <AbsoluteFill style={{ pointerEvents: 'none', color: '#fff' }}>
        <div style={{ position: 'absolute', left: `${titleStyle.x_pct ?? 8}%`, top: `${titleStyle.y_pct ?? 8}%`, fontSize: Number(titleStyle.font_size || 62), fontWeight: 900, color: titleStyle.color || '#fff', textTransform: 'uppercase', textShadow: '0 3px 12px #000' }}>{manifest.narrative.title}{manifest.narrative.category ? ` — ${manifest.narrative.category}` : ''}</div>
        <div style={{ position: 'absolute', right: '5%', top: '25%', width: '42%', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {rows.map((row) => <div key={row.rank} style={{ opacity: row.revealed ? 1 : 0.38, color: row.active ? (row.text_style?.accent_color || '#FFD400') : '#fff', fontSize: row.active ? 31 : 24, fontWeight: 900, textShadow: '0 2px 8px #000', padding: '5px 8px', borderRight: row.active ? `4px solid ${row.text_style?.accent_color || '#FFD400'}` : '4px solid transparent' }}><span style={{ color: row.active ? (row.text_style?.accent_color || '#FFD400') : '#aaa' }}>#{row.rank}</span>{row.revealed && row.label ? `  ${row.label}` : ''}</div>)}
        </div>
        {entry?.label && <div style={{ position: 'absolute', left: `${entry.text_style?.x_pct ?? 8}%`, top: `${entry.text_style?.y_pct ?? 34}%`, fontSize: Number(entry.text_style?.font_size || 54), fontWeight: 900, color: entry.text_style?.color || '#fff', textTransform: 'uppercase', textShadow: '0 4px 18px #000', maxWidth: '75%' }}>{entry.label}</div>}
      </AbsoluteFill>
      {final && <AbsoluteFill style={{ background: `rgba(0,0,0,${Math.max(0, Math.min(0.9, Number(manifest.reveal?.darkness ?? 0.35)))})`, pointerEvents: 'none' }} />}
    </AbsoluteFill>
  );
}

function RevealCompilationComposition({ codex, session: sessionProp, revealManifest, musicTimeline }) {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const session = sessionProp || {};
  const manifest = normalizeRevealManifest(revealManifest, fps, durationInFrames);
  const scene = revealSceneAtFrame(manifest, frame);
  const source = revealSourceForScene(manifest, scene);
  const localFrame = Math.max(0, frame - Number(scene?.start_frame || 0));
  const sourceUrl = source?.file ? staticFile(source.file.replace(/^\.\//, '')) : null;
  const music = normalizeMusicTimeline(musicTimeline || session.music || {}, fps, durationInFrames);
  const musicUrl = music.audio_src ? staticFile(music.audio_src.replace(/^\.\//, '')) : null;
  const audioSegments = musicUrl ? buildAudioSegments({ ...music, audio_src: musicUrl }, fps, durationInFrames) : [];
  const isFinal = Boolean(scene?.final_reveal);
  const finalStart = Number(scene?.start_frame || manifest.final_start_frame || 0);
  const reveal = manifest.reveal || {};
  const shakeFrames = Math.max(1, Number(reveal.shake_duration_frames || 12));
  const shakeLocal = frame - finalStart - Number(reveal.impact_frame_offset || 0);
  const shaking = isFinal && shakeLocal >= 0 && shakeLocal < shakeFrames;
  const shakeAmp = shaking ? (Number(reveal.shake_power || 0) / 100) * 34 * Math.pow(1 - shakeLocal / shakeFrames, 1.7) : 0;
  const shakeY = shaking ? Math.sin(shakeLocal * 2.8) * shakeAmp : 0;
  const sceneTransform = `${revealMotionTransform(scene, frame, fps)} translateY(${shakeY.toFixed(2)}px)`;
  const background = session.background || {};
  const label = isFinal ? manifest.narrative.this_one_label : manifest.narrative.others_label;
  return (
    <AbsoluteFill style={{ backgroundColor: background.color || '#050505', overflow: 'hidden' }}>
      {musicUrl && audioSegments.map((segment, index) => (
        <Sequence key={`reveal_audio_${index}`} from={segment.from} durationInFrames={segment.duration}>
          <Audio src={musicUrl} startFrom={segment.startFrom} volume={segment.volume} />
        </Sequence>
      ))}
      <AbsoluteFill style={{ transform: sceneTransform, transformOrigin: 'center center' }}>
        {sourceUrl && <Video src={sourceUrl} startFrom={localFrame} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
      </AbsoluteFill>
      <AbsoluteFill style={{ pointerEvents: 'none', padding: '6% 6%', justifyContent: 'space-between', color: '#fff', fontFamily: session.texts_style?.font || 'Impact, Arial Black, sans-serif' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: 42, fontWeight: 900, textShadow: '0 3px 12px #000' }}>
          <span>{manifest.narrative.theme}</span><span>{label}</span>
        </div>
        <div style={{ alignSelf: 'center', textAlign: 'center', fontSize: isFinal ? 118 : 58, lineHeight: 0.95, color: '#fff', textTransform: 'uppercase', textShadow: '0 4px 18px #000' }}>
          {isFinal ? (manifest.narrative.final_text || label) : (manifest.narrative.transition_text && frame === scene?.start_frame ? manifest.narrative.transition_text : '')}
        </div>
      </AbsoluteFill>
      {isFinal && <AbsoluteFill style={{ background: `rgba(0,0,0,${Math.max(0, Math.min(0.9, Number(reveal.darkness || 0)))})`, pointerEvents: 'none' }} />}
    </AbsoluteFill>
  );
}

export const OmniComposition = ({ codex, videoSrc, session: sessionProp, sequences, hybridManifest, hybridIntroSrc, musicTimeline, revealManifest, purManifest }) => {
  if (sessionProp?.review_mode === 'pur_pack' || purManifest?.mode === 'pur_pack') {
    return <PurPackComposition purManifest={purManifest || sessionProp?.pur_manifest} />;
  }
  if (sessionProp?.review_mode === 'ranking_compilation' || revealManifest?.mode === 'ranking_compilation') {
    return <RankingCompilationComposition session={sessionProp} rankingManifest={revealManifest || sessionProp?.ranking} musicTimeline={musicTimeline} />;
  }
  if (revealManifest?.mode === 'reveal_compilation' || sessionProp?.review_mode === 'reveal_compilation') {
    return <RevealCompilationComposition codex={codex} session={sessionProp} revealManifest={revealManifest || sessionProp?.reveal} musicTimeline={musicTimeline} />;
  }
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  const clip = codex || {};
  const session = sessionProp || clip.session || SESSION_FALLBACK;
  const presets = { ...SESSION_FALLBACK.presets, ...(session.presets || {}) };
  const textsStyle = { ...SESSION_FALLBACK.texts_style, ...(session.texts_style || {}) };
  const composition = getCompositionConfig(clip, session);
  const sceneRotation = composition.rotation_layer === 'composition'
    ? rotationForSequence(composition, 0, frame, fps, durationInFrames)
    : 0;

  const src = videoSrc || (clip.video?.source ? './' + clip.video.source : './clip_001.mp4');
  const videoUrl = src.startsWith('./') ? staticFile(src.replace('./', '')) : src;

  if (!clip || !clip.video) {
    return (
      <AbsoluteFill style={{ backgroundColor: '#ff4400', justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ color: 'white', fontSize: 64, fontWeight: 'bold' }}>CODEX MANQUANT</div>
      </AbsoluteFill>
    );
  }

  // â”€â”€ Zoom / slow-mo / shake / coup brutal â”€â”€
  const currentZoom = getCurrentZoom(frame, clip.zoom_keyframes || []);
  // Le slider Contraste (session) pilote le contrast() du filtre global.
  const contrastValue = presets.contrast ?? 1.3;
  const baseFilter = presets.color_css_filter || '';
  const colorFilter = baseFilter.includes('contrast')
    ? baseFilter.replace(/contrast\([^)]*\)/g, `contrast(${contrastValue})`)
    : `contrast(${contrastValue}) ${baseFilter}`.trim();
  // Le slider Luminosité (session) pilote le brightness() du filtre global.
  const brightnessValue = presets.brightness ?? 1.1;
  const brightnessFilter = colorFilter.includes('brightness')
    ? colorFilter.replace(/brightness\([^)]*\)/g, `brightness(${brightnessValue})`)
    : `${colorFilter} brightness(${brightnessValue})`.trim();
  const enhanceFilter = presets.enhance_4k
    ? ' contrast(1.15) saturate(1.2) brightness(1.08)'
    : '';
  const sharpening = presets.sharpening || 0;
  let sharpFilter = '';
  if (sharpening > 0) {
    const s = sharpening / 100;
    sharpFilter = ` contrast(${1 + s * 0.15}) drop-shadow(0 0 ${s * 0.5}px rgba(255,255,255,${s * 0.15}))`;
  }
  const darkLuxuryNoir = presets.dark_luxury_noir || {};
  const darkLuxuryFilter = darkLuxuryNoir.enabled
    ? darkLuxuryNoirFilter(darkLuxuryNoir.intensity)
    : '';
  const sciFiNeonHdr = presets.scifi_neon_hdr || {};
  const sciFiFilter = sciFiNeonHdr.enabled
    ? sciFiNeonHdrFilter(sciFiNeonHdr.intensity)
    : '';
  const fullFilter = (brightnessFilter + enhanceFilter + sharpFilter + ` ${darkLuxuryFilter} ${sciFiFilter}`).trim();
  const music = normalizeMusicTimeline(musicTimeline || session.music || clip.music || {}, fps, durationInFrames);
  const hybridState = hybridManifest ? hybridTimelineFrame(hybridManifest, frame, session, music) : null;
  const musicUrl = music.audio_src ? (music.audio_src.startsWith('./') ? staticFile(music.audio_src.replace(/^\.\//, '')) : music.audio_src) : null;
  const musicSegments = musicUrl ? buildAudioSegments({ ...music, audio_src: musicUrl }, fps, durationInFrames) : [];
  const segmentVolume = (segment) => {
    const localFrame = frame - segment.from;
    const fadeIn = segment.fade_in_frames ? interpolate(localFrame, [0, segment.fade_in_frames], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) : 1;
    const fadeOut = segment.fade_out_frames ? interpolate(localFrame, [Math.max(0, segment.duration - segment.fade_out_frames), segment.duration], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) : 1;
    return segment.volume * Math.min(fadeIn, fadeOut);
  };
  const matchCutEffectsActive = !hybridState || !hybridState.isIntro;
  const activeSceneFilter = matchCutEffectsActive ? fullFilter : '';

  const slowmoStart = clip.slowmo_start_frame || 0;
  const slowmoSpeed = clip.slowmo_speed || 1.0;
  const isSlowmo = frame >= slowmoStart && slowmoSpeed < 1.0;
  const playbackRate = isSlowmo ? slowmoSpeed : 1.0;

  const shakePower = clip.shake_power || 0;
  const shakeFrame = slowmoStart;
  const shakeDuration = 20;
  const isShaking = shakePower > 0 && frame >= shakeFrame && frame < shakeFrame + shakeDuration;
  let shakeX = 0, shakeY = 0;
  if (isShaking) {
    const shakeProgress = (frame - shakeFrame) / shakeDuration;
    const decay = Math.pow(1 - shakeProgress, 2);
    const amp = (shakePower / 100) * decay * 20;
    shakeY = Math.sin((frame - shakeFrame) * 0.8) * amp;
  }

  const brutalInterval = clip.brutal_cut_interval_frames || 0;
  const frameInBrutal = brutalInterval > 0 ? frame % brutalInterval : 999;
  const isBrutalCut = brutalInterval > 0 && frameInBrutal < 5;
  const brutalFlash = isBrutalCut ? 0.45 * (1 - frameInBrutal / 5) : 0;
  const brutalScale = isBrutalCut ? 1.04 : 1;

  const zoomTransform = `scale(${currentZoom.scale * brutalScale}) translate(${
    (0.5 - currentZoom.target_x) * 100
  }%, ${(0.5 - currentZoom.target_y) * 100}%)`;

  const virtualSequences = normalizeSequences(sequences || clip.sequences_manifest || clip.sequences);
  const texts = clip.texts || {};
  const textMode = texts.mode || (texts.title ? 'title' : 'none');
  const hybridIntroUrl = hybridIntroSrc || (hybridManifest?.intro?.file ? staticFile(hybridManifest.intro.file.replace(/^\.\//, '')) : null);

  return (
    <AbsoluteFill style={{ backgroundColor: session.background?.color || '#000' }}>
      {/* Audio : même manifeste et mêmes segments que F03 Preview */}
      {musicUrl && musicSegments.map((segment, index) => (
        <Sequence key={`music_${index}`} from={segment.from} durationInFrames={segment.duration}>
          <Audio src={musicUrl} startFrom={segment.startFrom} volume={segmentVolume(segment)} />
        </Sequence>
      ))}
      {!musicUrl && clip.audio_enabled === true && clip.audioSrc && (
        <Audio src={staticFile(clip.audioSrc)} volume={clip.volume ?? 1} />
      )}

      {/* CALQUE 6 wrapper : presets globaux sur toute la scÃ¨ne */}
      <AbsoluteFill style={{
        filter: activeSceneFilter || undefined,
        transform: sceneRotation ? `rotate(${sceneRotation}deg)` : undefined,
        transformOrigin: 'center center',
        overflow: 'hidden',
      }}>
        {/* L1 BACKGROUND */}
        {session.background?.image ? (
          <AbsoluteFill style={{ overflow: 'hidden' }}>
            <Img
              src={staticFile(
                session.background.image.includes('/')
                  ? session.background.image
                  : `backgrounds/${session.background.image}`
              )}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                transform: `scale(${session.background.scale ?? 1})`,
                transformOrigin: 'center center',
              }}
            />
          </AbsoluteFill>
        ) : (
          <AbsoluteFill style={{ backgroundColor: session.background?.color || '#0a0a0a' }} />
        )}

        {/* L2 VIDEO : source horizontale, recadrage et séquences virtuelles */}
        {hybridState?.isIntro && hybridIntroUrl && (
          <AbsoluteFill style={{ overflow: 'hidden', zIndex: 1 }}>
            <Video src={hybridIntroUrl} muted startFrom={0} style={{ width: '100%', height: '100%', objectFit: composition.fit || 'cover' }} />
          </AbsoluteFill>
        )}
        {composition.background_fill === 'blurred_video' && (
          <AbsoluteFill style={{ overflow: 'hidden', backgroundColor: '#000' }}>
            <Video
              src={videoUrl}
              muted
              style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(24px) brightness(0.45)', transform: 'scale(1.18)' }}
            />
          </AbsoluteFill>
        )}
        {virtualSequences.length > 0 ? virtualSequences.map((sequence, sequenceIndex) => {
          const sequenceRotation = sequence.rotationDeg ?? rotationForSequence(composition, sequenceIndex, frame, fps, durationInFrames);
          const introOffset = hybridState ? hybridState.hybrid.intro.duration_frames : 0;
          const fit = sequence.fit || composition.fit || 'cover';
          const sequenceUrl = sequence.file
            ? staticFile(sequence.file.replace(/^\.\//, ''))
            : videoUrl;
          const sequenceStartFrom = sequence.file ? 0 : sequence.sourceStartFrame;
          const transform = `${zoomTransform} translate(${shakeX}px, ${shakeY}px) translateY(${session.video?.offset_y || 0}%) rotate(${sequenceRotation}deg)`;
          return (
            <Sequence key={sequence.id} from={sequence.timelineStartFrame + introOffset} durationInFrames={sequence.durationFrames}>
              <AbsoluteFill style={{ overflow: 'hidden' }}>
                <Video
                  src={sequenceUrl}
                  startFrom={sequenceStartFrom}
                  muted
                  style={{ width: '100%', height: '100%', objectFit: fit, transform, transformOrigin: 'center center', opacity: hybridState?.isIntro ? 0 : 1 }}
                  playbackRate={playbackRate}
                />
              </AbsoluteFill>
            </Sequence>
          );
        }) : (
          <AbsoluteFill style={{ overflow: 'hidden' }}>
            <Video
              src={videoUrl}
              muted
              style={{ width: '100%', height: '100%', objectFit: composition.fit || 'cover', transform: `${zoomTransform} rotate(${rotationForSequence(composition, 0, frame, fps, durationInFrames)}deg)`, transformOrigin: 'center center' }}
              playbackRate={playbackRate}
            />
          </AbsoluteFill>
        )}

        {/* L3 TITRE / DARK LUXURY FLASH TEXT */}
        {textMode === 'dark_luxury_flash_text' ? (
          <FlashTextBlock texts={texts} style={textsStyle} frame={frame} />
        ) : (textMode === 'title' || textMode === 'title+paragraph') && texts.title ? (
          <TitleBlock
            content={texts.title}
            style={textsStyle}
            box={textsStyle.title_box}
            offsetPct={texts.title_offset_pct ?? 8}
          />
        ) : null}
        {hybridState?.isIntroText && (
          <div style={{ ...hybridTextStyle(hybridState.hybrid.intro_text, frame), zIndex: 100 }}>{hybridState.hybrid.intro_text.text}</div>
        )}
        {hybridState?.isEgo && (
          <div style={{ ...hybridEgoStyle(hybridManifest, frame, session, music), zIndex: 101 }}>{hybridState.hybrid.ego.text}</div>
        )}

        {/* L4 PARAGRAPHE */}
        {textMode === 'title+paragraph' && texts.paragraph ? (
          <ParagraphBlock
            content={texts.paragraph}
            style={textsStyle}
            box={textsStyle.paragraph_box}
            offsetPct={texts.paragraph_offset_pct ?? 8}
          />
        ) : null}

        {/* L5 LOGO */}
        <LogoOverlay logo={session.logo || clip.logo} width={width} />

        {/* Badge SLOW MOTION */}
        {isSlowmo && (
          <AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'flex-end', padding: 40 }}>
            <div style={{
              backgroundColor: 'rgba(0,0,0,0.7)',
              color: '#FF4444',
              fontSize: 32,
              fontWeight: 'bold',
              padding: '8px 20px',
              borderRadius: 8,
              letterSpacing: '0.1em',
            }}>
              SLOW MOTION
            </div>
          </AbsoluteFill>
        )}

        {/* Text overlays rÃ©tro-compat — masquÃ©s quand les textes v4 sont actifs (doublon) */}
        {(textMode === 'none' || !texts.title) &&
          (clip.text_overlays || []).map((overlay, index) => {
            const startFrame = overlay.start_frame || 0;
            const endFrame = overlay.end_frame || durationInFrames;
            if (frame < startFrame || frame > endFrame) return null;
            return (
              <Sequence key={overlay.id || index} from={startFrame} durationInFrames={endFrame - startFrame + 1}>
                <TextOverlay overlay={overlay} frame={frame - startFrame} fps={fps} />
              </Sequence>
            );
          })}

        {/* Flash coup brutal */}
        {brutalFlash > 0 && (
          <AbsoluteFill style={{ backgroundColor: '#fff', opacity: brutalFlash, pointerEvents: 'none' }} />
        )}
      </AbsoluteFill>

      {/* Dark Luxury Noir : halo champagne et accents chauds au-dessus de l’image */}
      {matchCutEffectsActive && darkLuxuryNoir.enabled && (
        <AbsoluteFill style={darkLuxuryNoirOverlayStyle(darkLuxuryNoir.intensity)} />
      )}

      {/* Sci-Fi Neon HDR : accents cyan, vert néon et rouge/orange */}
      {matchCutEffectsActive && sciFiNeonHdr.enabled && (
        <AbsoluteFill style={sciFiNeonHdrOverlayStyle(sciFiNeonHdr.intensity)} />
      )}

      {/* Finitions : grain + vignette au-dessus de tout */}
      {matchCutEffectsActive && (presets.grain_intensity || 0) > 0 && (
        <AbsoluteFill style={{ opacity: presets.grain_intensity, pointerEvents: 'none', mixBlendMode: 'overlay' }}>
          <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
            <filter id="grainFilter">
              <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
              <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.5 0" />
            </filter>
            <rect width="100%" height="100%" filter="url(#grainFilter)" />
          </svg>
        </AbsoluteFill>
      )}
      {matchCutEffectsActive && (presets.vignette || 0) > 0 && (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,${presets.vignette}) 100%)`,
            pointerEvents: 'none',
          }}
        />
      )}
    </AbsoluteFill>
  );
};

/* â”€â”€ L3 TITRE â”€â”€ */
const FlashTextBlock = ({ texts, style, frame }) => {
  const unit = activeFlashTextUnit(texts, frame);
  if (!unit) return null;
  return <div style={flashTextStyle(unit, frame, style)}>{unit.text}</div>;
};

const TitleBlock = ({ content, style, box, offsetPct }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });

  const boxEnabled = box && box.enabled;
  const textStyle = boxEnabled
    ? {
        fontFamily: style.font,
        fontSize: `${style.size_title}px`,
        color: box.text_color || style.color,
        fontWeight: 900,
        textTransform: 'uppercase',
        lineHeight: 1.1,
        textAlign: 'center',
        backgroundColor: box.color || 'rgba(0,0,0,0.7)',
        border: (box.border_width || 0) > 0
          ? `${box.border_width}px solid ${box.border_color || '#FFFFFF'}`
          : 'none',
        borderRadius: `${box.radius || 0}px`,
        padding: `${box.padding || 12}px ${(box.padding || 12) * 1.6}px`,
        maxWidth: '88%',
        wordWrap: 'break-word',
      }
    : {
        fontFamily: style.font,
        fontSize: `${style.size_title}px`,
        color: style.color,
        WebkitTextStroke: `${style.stroke_width}px ${style.stroke_color}`,
        textShadow: style.shadow,
        letterSpacing: style.letter_spacing,
        fontWeight: 900,
        textTransform: 'uppercase',
        lineHeight: 1.1,
        textAlign: 'center',
        maxWidth: '88%',
        wordWrap: 'break-word',
      };

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        paddingTop: `${offsetPct}%`,
        pointerEvents: 'none',
      }}
    >
      <div style={{ ...textStyle, opacity }}>{content}</div>
    </AbsoluteFill>
  );
};

/* â”€â”€ L4 PARAGRAPHE â”€â”€ */
const ParagraphBlock = ({ content, style, box, offsetPct }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: 'clamp' });

  const boxEnabled = box && box.enabled;
  const textStyle = boxEnabled
    ? {
        fontFamily: style.font,
        fontSize: `${style.size_paragraph}px`,
        color: box.text_color || style.color,
        fontWeight: 700,
        lineHeight: 1.25,
        textAlign: 'center',
        backgroundColor: box.color || 'rgba(0,0,0,0.7)',
        border: (box.border_width || 0) > 0
          ? `${box.border_width}px solid ${box.border_color || '#FFFFFF'}`
          : 'none',
        borderRadius: `${box.radius || 0}px`,
        padding: `${box.padding || 12}px ${(box.padding || 12) * 1.6}px`,
        maxWidth: '88%',
      }
    : {
        fontFamily: style.font,
        fontSize: `${style.size_paragraph}px`,
        color: style.color,
        WebkitTextStroke: `${Math.max(1, style.stroke_width - 1)}px ${style.stroke_color}`,
        textShadow: style.shadow,
        letterSpacing: style.letter_spacing,
        fontWeight: 700,
        lineHeight: 1.25,
        textAlign: 'center',
        maxWidth: '88%',
        maxHeight: '22%',
        overflow: 'hidden',
        display: '-webkit-box',
        WebkitLineClamp: 4,
        WebkitBoxOrient: 'vertical',
        wordWrap: 'break-word',
      };

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: `${offsetPct}%`,
        pointerEvents: 'none',
      }}
    >
      <div style={{ ...textStyle, opacity }}>{content}</div>
    </AbsoluteFill>
  );
};

/* â”€â”€ L5 LOGO â”€â”€ */
const LogoOverlay = ({ logo, width }) => {
  if (!logo || !logo.src) return null;
  const logoWidth = Math.round(width * ((logo.width_pct || 20) / 100));
  const pos = getLogoPosition(logo);
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', ...pos, opacity: logo.opacity ?? 1 }}>
        <Img src={staticFile(logo.src)} style={{ width: logoWidth, height: 'auto' }} />
      </div>
    </AbsoluteFill>
  );
};

function getLogoPosition(logo) {
  const pad = 40;
  const position = logo.position || 'bottom_left';
  if (position === 'custom') {
    return {
      left: `${logo.x_pct ?? 50}%`,
      top: `${logo.y_pct ?? 50}%`,
      transform: 'translate(-50%, -50%)',
    };
  }
  switch (position) {
    case 'top_center':
      return { top: pad, left: '50%', transform: 'translateX(-50%)' };
    case 'top_right':
      return { top: pad, right: pad };
    case 'bottom_center':
      return { bottom: pad, left: '50%', transform: 'translateX(-50%)' };
    case 'bottom_right':
      return { bottom: pad, right: pad };
    case 'top_left':
      return { top: pad, left: pad };
    case 'bottom_left':
    default:
      return { bottom: pad, left: pad };
  }
}

/* â”€â”€ TextOverlay rÃ©tro-compat v3 â”€â”€ */
const TextOverlay = ({ overlay, frame, fps }) => {
  const {
    content,
    animation = 'word_by_word',
    font = 'Impact, Arial Black, sans-serif',
    size = 96,
    color = '#FFFFFF',
    stroke_color = '#000000',
    stroke_width = 4,
    shadow = '2px 4px 8px rgba(0,0,0,0.9)',
    position = 'center',
    letter_spacing = '0em',
    glow_intensity = 0,
    start_frame = 0,
  } = overlay;

  const words = content.split(' ');
  const totalDuration = (overlay.end_frame || 300) - start_frame;
  const wordFadeFrames = 8;
  let wordsPerFrame = 0;
  if (animation === 'word_by_word') {
    const revealDuration = Math.max(totalDuration * 0.6, words.length * 8);
    wordsPerFrame = revealDuration / words.length;
  }

  const glowLayers = [];
  if (glow_intensity > 0) {
    const layers = Math.round((glow_intensity / 100) * 4);
    const glowSizes = [3, 6, 12, 20];
    for (let i = 0; i < layers; i++) glowLayers.push(`0 0 ${glowSizes[i]}px ${color}`);
    glowLayers.push(shadow);
  } else {
    glowLayers.push(shadow);
  }
  const textShadowStr = glowLayers.join(', ');
  const strokeStr = stroke_width > 0 ? `${stroke_width}px ${stroke_color}` : '0px transparent';

  const baseTextStyle = {
    fontFamily: font,
    fontSize: `${size}px`,
    color,
    WebkitTextStroke: strokeStr,
    textShadow: textShadowStr,
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
  };

  const positionStyle = getPositionStyle(position);

  let blockOpacity = 1;
  let blockScale = 1;
  if (animation === 'pop') {
    blockOpacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: 'clamp' });
    blockScale = interpolate(frame, [0, 6], [0.8, 1], { extrapolateRight: 'clamp' });
  } else if (animation === 'fade_in') {
    blockOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  } else if (animation === 'fade_in_slow') {
    blockOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
  }

  if (animation === 'word_by_word') {
    return (
      <div style={positionStyle}>
        <div style={{ ...baseTextStyle, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center' }}>
          {words.map((word, i) => {
            const wordLocalFrame = frame - i * wordsPerFrame;
            const wordOpacity = interpolate(wordLocalFrame, [0, wordFadeFrames], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            });
            const wordScale = interpolate(wordLocalFrame, [0, wordFadeFrames], [0.92, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            });
            return (
              <span key={i} style={{ opacity: wordOpacity, transform: `scale(${wordScale})`, display: 'inline-block', transition: 'none' }}>
                {word}
                {i < words.length - 1 ? '\u00A0' : ''}
              </span>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div style={positionStyle}>
      <div style={{ ...baseTextStyle, opacity: blockOpacity, transform: `scale(${blockScale})` }}>
        {content}
      </div>
    </div>
  );
};

function getPositionStyle(position) {
  switch (position) {
    case 'center':
      return { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '90%' };
    case 'top':
      return { position: 'absolute', top: '10%', left: '50%', transform: 'translateX(-50%)', width: '90%' };
    case 'center_bottom':
      return { position: 'absolute', bottom: '15%', left: '50%', transform: 'translateX(-50%)', width: '90%' };
    case 'bottom':
      return { position: 'absolute', bottom: '8%', left: '50%', transform: 'translateX(-50%)', width: '90%' };
    case 'center_left':
      return { position: 'absolute', top: '45%', left: '10%', width: '80%' };
    default:
      return { position: 'absolute', bottom: '15%', left: '50%', transform: 'translateX(-50%)', width: '90%' };
  }
}

function getCurrentZoom(frame, keyframes) {
  if (!keyframes || keyframes.length === 0) {
    return { scale: 1.0, target_x: 0.5, target_y: 0.5 };
  }
  if (frame <= keyframes[0].frame) {
    return { scale: keyframes[0].scale, target_x: keyframes[0].target_x, target_y: keyframes[0].target_y };
  }
  if (frame >= keyframes[keyframes.length - 1].frame) {
    const last = keyframes[keyframes.length - 1];
    return { scale: last.scale, target_x: last.target_x, target_y: last.target_y };
  }
  for (let i = 0; i < keyframes.length - 1; i++) {
    const k1 = keyframes[i];
    const k2 = keyframes[i + 1];
    if (frame >= k1.frame && frame <= k2.frame) {
      const t = (frame - k1.frame) / (k2.frame - k1.frame);
      const easedT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      return {
        scale: k1.scale + (k2.scale - k1.scale) * easedT,
        target_x: k1.target_x + (k2.target_x - k1.target_x) * easedT,
        target_y: k1.target_y + (k2.target_y - k1.target_y) * easedT,
      };
    }
  }
  return { scale: 1.0, target_x: 0.5, target_y: 0.5 };
}
