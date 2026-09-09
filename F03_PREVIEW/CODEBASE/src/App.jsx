import React, { useState, useEffect, useRef } from 'react';
import { Player } from '@remotion/player';
import { OmniComposition } from './preview/OmniComposition';
import { COMPOSITION_PRESETS, getCompositionConfig } from './preview/compositionConfig';
import { normalizeHybridManifest } from './preview/hybridNarrative';
import { normalizeMusicTimeline, musicWaveformPoints } from './preview/audioTimeline';
import { normalizeRevealManifest } from './preview/revealCompilation';
import { normalizeRankingManifest } from './preview/rankingCompilation';
import { parsePurPack } from './preview/bridgeClipper';

/**
 * App — F03 PREVIEW (v4.0 — session + clips)
 *
 * Charge le codex.json (bloc session + clips) et le clip 9:16 depuis public/,
 * rend la composition en temps réel via @remotion/player.
 *
 * L'opérateur ajuste la SESSION (style global appliqué aux N clips) :
 *  - Fond : menu déroulant des PNG déposés dans public/backgrounds/ (dossier
 *    dédié, comme CRUSADER) ou couleur unie + échelle
 *  - Logo : taille (pas déplaçable — le pack impose le placement)
 *  - Textes : mode titre seul / titre+paragraphe (titre haut, paragraphe bas)
 *  - Presets : couleurs, 4K, netteté, grain, vignette, volume, coup brutal
  *  - Export codex.json validé (validated_by_magos: true)
 */
function buildFlashUnits(content, previous = []) {
  const words = String(content || '').trim().split(/\s+/).filter(Boolean);
  return words.map((word, index) => ({
    id: previous[index]?.id || `word_${String(index + 1).padStart(3, '0')}`,
    text: word,
    start_frame: previous[index]?.start_frame ?? 0,
    duration_frames: previous[index]?.duration_frames ?? 8,
    impact: previous[index]?.impact ?? false,
    rotation_deg: previous[index]?.rotation_deg ?? 0,
    scale: previous[index]?.scale ?? 1,
    blur_frames: previous[index]?.blur_frames ?? 0,
  }));
}

export default function App() {
  const [codex, setCodex] = useState(null);        // codex complet (session + clips)
  const [clip, setClip] = useState(null);          // clip en cours d'édition
  const [session, setSession] = useState(null);    // session (style global)
  const [videoSrc, setVideoSrc] = useState('');
  const [backgrounds, setBackgrounds] = useState([]); // liste des fonds PNG
  const [sequences, setSequences] = useState(null); // manifeste virtuel produit par F00
  const [hybridManifest, setHybridManifest] = useState(null);
  const [hybridIntroSrc, setHybridIntroSrc] = useState('');
  const [revealManifest, setRevealManifest] = useState(null);
  const [rankingManifest, setRankingManifest] = useState(null);
  const [purPackRaw, setPurPackRaw] = useState(null);      // production_pack_pur_*.json brut (PERTURABO)
  const [purManifest, setPurManifest] = useState(null);    // manifeste dev10.pur.v1 converti
  const [purCanvas, setPurCanvas] = useState('9:16');      // 9:16 | 16:9 | 1:1
  const [audioSrc, setAudioSrc] = useState('');
  const [audioPosition, setAudioPosition] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [musicTimeline, setMusicTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [validated, setValidated] = useState(false);
  const [activeTab, setActiveTab] = useState('text');
  const [flashSelectedIndex, setFlashSelectedIndex] = useState(0);
  const [logoPending, setLogoPending] = useState(null); // {x_pct, y_pct} balise double-clic
  const [waveDrag, setWaveDrag] = useState(null);
  const playerRef = useRef(null);
  const audioPlayerRef = useRef(null);
  const waveformRef = useRef(null);
  const lastClickRef = useRef({ t: 0, x: 0, y: 0 });

  // En mode Flash Text, l’édition doit être immédiatement visible : pause et
  // retour au début de l’unité sélectionnée pour régler son style sans attendre.
  useEffect(() => {
    if (!clip?.texts || clip.texts.mode !== 'dark_luxury_flash_text') return;
    const units = clip.texts.units?.length
      ? clip.texts.units
      : buildFlashUnits(clip.texts.content || clip.texts.title || '', []);
    if (!units.length || !playerRef.current) return;
    const selected = units[Math.min(flashSelectedIndex, units.length - 1)];
    const startFrame = units
      .slice(0, Math.min(flashSelectedIndex, units.length - 1))
      .reduce((sum, unit) => sum + Math.max(1, Number(unit.duration_frames) || 8), 0);
    playerRef.current.pause();
    playerRef.current.seekTo(selected?.start_frame > 0 ? selected.start_frame : startFrame);
  }, [clip?.texts?.mode, clip?.texts?.content, clip?.texts?.units, flashSelectedIndex]);

  // Charger le codex.json (v4 : session + clips), la vidéo et les fonds
  useEffect(() => {
    async function loadAssets() {
      try {
        const codexResp = await fetch('./codex.json');
        if (!codexResp.ok) throw new Error('codex.json non trouvé dans public/');
        const full = await codexResp.json();
        const clipFirst = full.clips?.[0] || full;
        setCodex(full);
        setClip(clipFirst);
        setSession(full.session || {});
        let loadedMusic = null;
        try {
          const musicResp = await fetch('./music_timeline.json');
          if (musicResp.ok) loadedMusic = await musicResp.json();
        } catch (_) { /* audio optionnel */ }
        const selectedMusic = full.session?.music || clipFirst.music || loadedMusic || {};
        setMusicTimeline(normalizeMusicTimeline(selectedMusic, Number(clipFirst.video?.fps || 30), Number(clipFirst.video?.total_frames || 300)));
        if (selectedMusic.audio_src) setAudioSrc(selectedMusic.audio_src);
        try {
          const revealResp = await fetch('./reveal_sources.json');
          if (revealResp.ok) setRevealManifest(await revealResp.json());
          else if (full.session?.reveal) setRevealManifest(full.session.reveal);
        } catch (_) {
          if (full.session?.reveal) setRevealManifest(full.session.reveal);
        }
        try {
          const rankingResp = await fetch('./ranking_manifest.json');
          if (rankingResp.ok) setRankingManifest(await rankingResp.json());
          else if (full.session?.ranking) setRankingManifest(full.session.ranking);
        } catch (_) {
          if (full.session?.ranking) setRankingManifest(full.session.ranking);
        }
        try {
          const purResp = await fetch('./pur_manifest.json');
          if (purResp.ok) setPurManifest(await purResp.json());
          else if (full.session?.pur_manifest) setPurManifest(full.session.pur_manifest);
        } catch (_) {
          if (full.session?.pur_manifest) setPurManifest(full.session.pur_manifest);
        }
        setActiveTab(full.session?.review_mode === 'hybrid_narrative' ? 'hybrid' : full.session?.review_mode === 'reveal_compilation' ? 'reveal' : full.session?.review_mode === 'ranking_compilation' ? 'ranking' : full.session?.review_mode === 'pur_pack' ? 'pur' : 'text');
        setVideoSrc(clipFirst.video?.source ? './' + clipFirst.video.source : './video_source.mp4');
        try {
          const motionResp = await fetch('./motion_slow_manifest.json');
          if (motionResp.ok) {
            setSequences(await motionResp.json());
          } else {
            const seqResp = await fetch('./sequences.json');
            if (seqResp.ok) setSequences(await seqResp.json());
          }
        } catch (e) {
          try {
            const seqResp = await fetch('./sequences.json');
            if (seqResp.ok) setSequences(await seqResp.json());
          } catch (_) {
            setSequences(null);
          }
        }
        try {
          const hybridResp = await fetch('./hybrid_manifest.json');
          if (hybridResp.ok) {
            const hybrid = await hybridResp.json();
            setHybridManifest(hybrid);
            const matchRef = hybrid.match_cut?.manifest;
            if (matchRef) {
              const matchResp = await fetch('./' + matchRef.replace(/^\.\//, ''));
              if (matchResp.ok) setSequences(await matchResp.json());
            }
          }
        } catch (_) {
          setHybridManifest(null);
        }
        // Liste des fonds PNG (écrite par le transit F02 / bridge)
        try {
          const bgResp = await fetch('./backgrounds/manifest.json');
          if (bgResp.ok) {
            const bg = await bgResp.json();
            setBackgrounds(Array.isArray(bg) ? bg : (bg.files || []));
          }
        } catch (e) {
          setBackgrounds([]); // pas de dossier fonds — menu vide
        }
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }
    loadAssets();
  }, []);

  if (loading) {
    return (
      <div style={styles.loading}>
        <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳ Chargement...</div>
        <div style={{ fontSize: '14px', color: '#666' }}>Lecture du codex.json, de la vidéo source, des séquences et des fonds</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.loading}>
        <div style={{ fontSize: '24px', color: '#ff4444', marginBottom: '10px' }}>❌ Erreur</div>
        <div style={{ fontSize: '14px', color: '#888' }}>{error}</div>
        <div style={{ marginTop: '20px', fontSize: '13px', color: '#666', textAlign: 'left' }}>
          <strong>Setup requis:</strong>
          <br />1. Placez <code>codex.json</code> dans <code>public/</code>
          <br />2. Placez <code>video_source.mp4</code> dans <code>public/</code>
          <br />3. Placez <code>sequences.json</code> dans <code>public/</code>
          <br />4. Placez vos fonds PNG dans <code>public/backgrounds/</code>
          <br />5. Lancez <code>npm run dev</code>
        </div>
      </div>
    );
  }

  const fps = clip.video?.fps || 30;
  const baseTotalFrames = sequences?.total_frames || clip.video?.total_frames || 300;
  const reviewMode = session.review_mode || 'match_cut';
  const musicForHybrid = normalizeMusicTimeline(musicTimeline || session.music || {}, fps, baseTotalFrames);
  const activeHybrid = reviewMode === 'hybrid_narrative' ? normalizeHybridManifest(
    hybridManifest || {
      mode: 'hybrid_narrative',
      fps,
      match_cut: { total_frames: baseTotalFrames },
      intro: session.hybrid?.intro || {},
      intro_text: session.hybrid?.intro_text || {},
      ego: session.hybrid?.ego || {},
    }, session, musicForHybrid
  ) : null;
  const activeReveal = reviewMode === 'reveal_compilation' ? normalizeRevealManifest(revealManifest || session.reveal || {}, fps, baseTotalFrames) : null;
  const activeRanking = reviewMode === 'ranking_compilation' ? normalizeRankingManifest(rankingManifest || session.ranking || {}, fps, baseTotalFrames) : null;
  const totalFrames = activeRanking?.total_frames || activeReveal?.total_frames || activeHybrid?.total_frames || baseTotalFrames;
  const composition = getCompositionConfig(clip, session);
  const music = normalizeMusicTimeline(musicTimeline || session.music || {}, fps, totalFrames);
  const waveformWidth = 600;
  const waveformHeight = 82;
  const waveformDuration = Math.max(
    Number(music.duration_seconds || 0),
    Number(music.loop_out || 0),
    Number(music.climax_time || 0),
    Number(music.beats?.[music.beats.length - 1]?.time_seconds || 0),
    1,
  );
  const waveform = musicWaveformPoints(music.beats, waveformWidth, waveformHeight);
  const waveformX = (seconds) => Math.max(0, Math.min(waveformWidth, (Number(seconds || 0) / waveformDuration) * waveformWidth));
  const updateReveal = (patch) => {
    setRevealManifest((current) => {
      const next = { ...(current || {}), ...patch };
      setSession((s) => ({ ...s, reveal: next }));
      return next;
    });
  };
  const updateRanking = (patch) => {
    setRankingManifest((current) => {
      const next = { ...(current || {}), ...patch };
      setSession((s) => ({ ...s, ranking: next }));
      return next;
    });
  };
  const updateRankingNarrative = (key, value) => updateRanking({ narrative: { ...(rankingManifest?.narrative || {}), [key]: value } });
  // PUR : convertit un pack PERTURABO brut en manifeste dev10.pur.v1 côté navigateur
  const convertPurPack = (pack, canvas) => {
    if (!pack) return;
    const manifest = parsePurPack(pack, { fps, canvas: canvas || purCanvas, clipFiles: [`clips/pur_${pack.identite?.angle_id || pack.pack_id || 'clip'}.mp4`] });
    setPurManifest(manifest);
    setSession((s) => ({ ...s, review_mode: 'pur_pack', pur_manifest: manifest }));
    setActiveTab('pur');
  };
  const updatePurOverlayLine = (lineIndex, text) => {
    setPurManifest((current) => {
      if (!current) return current;
      const lines = [...(current.narrative?.overlay?.lines || [])];
      lines[lineIndex] = text;
      const next = { ...current, narrative: { ...current.narrative, overlay: { ...current.narrative?.overlay, lines } } };
      setSession((s) => ({ ...s, pur_manifest: next }));
      return next;
    });
  };
  const updateRankingEntry = (index, patch) => {
    const entries = [...(rankingManifest?.entries || [])];
    entries[index] = { ...(entries[index] || {}), ...patch };
    updateRanking({ entries });
  };
  const updateRevealNarrative = (key, value) => {
    updateReveal({ narrative: { ...(revealManifest?.narrative || {}), [key]: value } });
  };
  const updateRevealSource = (index, key, value) => {
    const sources = [...(revealManifest?.sources || [])];
    sources[index] = { ...(sources[index] || {}), [key]: value };
    updateReveal({ sources });
  };
  const updateRevealScene = (index, key, value) => {
    const scenes = [...(revealManifest?.scenes || [])];
    scenes[index] = { ...(scenes[index] || {}), [key]: value };
    updateReveal({ scenes });
  };
  const updateMusic = (key, value) => {
    const next = normalizeMusicTimeline({ ...music, [key]: value }, fps, totalFrames);
    setMusicTimeline(next);
    setSession((s) => ({ ...s, music: next }));
  };
  const updateMusicBlock = (block, key, value) => {
    const next = normalizeMusicTimeline({ ...music, [block]: { ...(music[block] || {}), [key]: value } }, fps, totalFrames);
    setMusicTimeline(next);
    setSession((s) => ({ ...s, music: next }));
  };
  const waveTimeFromEvent = (event) => {
    const rect = waveformRef.current?.getBoundingClientRect();
    if (!rect || !rect.width) return 0;
    const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    return ratio * waveformDuration;
  };
  const seekAudio = (seconds) => {
    const element = audioPlayerRef.current;
    if (!element) return;
    const next = Math.max(0, Math.min(Number.isFinite(element.duration) ? element.duration : waveformDuration, seconds));
    element.currentTime = next;
    setAudioPosition(next);
  };
  const seekAudioFromEvent = (event) => {
    if (event.target !== event.currentTarget) return;
    seekAudio(waveTimeFromEvent(event));
  };
  const toggleAudioPlayback = async () => {
    const element = audioPlayerRef.current;
    if (!element) return;
    if (element.paused) await element.play();
    else element.pause();
  };
  const setWaveHandleTime = (handle, rawSeconds) => {
    const seconds = Math.max(0, Math.min(waveformDuration, rawSeconds));
    if (handle === 'loop_in') {
      updateMusicBlock('intro', 'in_seconds', Number(Math.min(seconds, Math.max(0, music.intro_out - 0.05)).toFixed(2)));
    } else if (handle === 'loop_out') {
      updateMusicBlock('intro', 'out_seconds', Number(Math.max(seconds, music.intro_in + 0.05).toFixed(2)));
    } else if (handle === 'climax' || handle === 'match_cut_in') {
      const nextIn = Number(seconds.toFixed(2));
      updateMusicBlock('match_cut', 'in_seconds', nextIn);
    } else if (handle === 'match_cut_out') {
      updateMusicBlock('match_cut', 'out_seconds', Number(Math.max(seconds, music.match_cut_in + 0.05).toFixed(2)));
    }
  };
  const beginWaveDrag = (event, handle) => {
    event.preventDefault();
    waveformRef.current?.setPointerCapture?.(event.pointerId);
    setWaveDrag(handle);
    setWaveHandleTime(handle, waveTimeFromEvent(event));
  };

  const motionSlow = {
    enabled: false,
    mode: 'off',
    speed: 0.5,
    ranges: '',
    engine: 'ffmpeg_minterpolate',
    ...(session.motion_slow || {}),
  };
  const vidWidth = composition.width;
  const vidHeight = composition.height;

  // ── Helpers session ──
  const updateSession = (section, key, value) => {
    const newSession = {
      ...session,
      [section]: { ...(session[section] || {}), [key]: value },
    };
    setSession(newSession);
  };
  const updateClip = (key, value) => setClip({ ...clip, [key]: value });
  const updateTexts = (key, value) => setClip((current) => ({
    ...current,
    texts: { ...(current?.texts || {}), [key]: value },
  }));
  const updateFlashUnits = (units) => updateTexts('units', units);
  const updateFlashUnit = (index, patch) => setClip((currentClip) => {
    const current = currentClip?.texts?.units || [];
    return {
      ...currentClip,
      texts: {
        ...(currentClip?.texts || {}),
        units: current.map((unit, i) => i === index ? { ...unit, ...patch } : unit),
      },
    };
  });
  const updateSessionTextsStyle = (key, value) =>
    updateSession('texts_style', key, value);
  const updatePreset = (key, value) => updateSession('presets', key, value);
  const updateComposition = (key, value) => setSession((s) => ({
    ...s,
    composition: { ...(s.composition || {}), [key]: value },
  }));
  const updateReviewMode = (value) => {
    setSession((s) => ({ ...s, review_mode: value }));
    setActiveTab(value === 'hybrid_narrative' ? 'hybrid' : value === 'reveal_compilation' ? 'reveal' : value === 'ranking_compilation' ? 'ranking' : 'text');
  };

  // ── Balise logo : double-clic sur la vidéo → poser ici ──
  const handleLogoClick = (e) => {
    const now = Date.now();
    const last = lastClickRef.current;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX, y = e.clientY;
    const isDouble = now - last.t < 350 && Math.abs(x - last.x) < 12 && Math.abs(y - last.y) < 12;
    lastClickRef.current = { t: now, x, y };
    if (!isDouble) return;
    const xPct = Math.round(((x - rect.left) / rect.width) * 1000) / 10;
    const yPct = Math.round(((y - rect.top) / rect.height) * 1000) / 10;
    setLogoPending({ x_pct: xPct, y_pct: yPct });
  };

  const confirmLogoPlacement = (ok) => {
    if (ok && logoPending) {
      // FIX: update atomique — les 3 updateSession séquentielles lisaient le
      // même `session` obsolète (closure) et React les batchait : seule la
      // dernière (y_pct) survivait, position/custom et x_pct étaient perdus.
      setSession((s) => ({
        ...s,
        logo: {
          ...(s.logo || {}),
          position: 'custom',
          x_pct: logoPending.x_pct,
          y_pct: logoPending.y_pct,
        },
      }));
    }
    setLogoPending(null);
  };

  // ── Helpers panneaux texte (fond/bord/coins) ──
  const updateTextBox = (boxKey, key, value) => {
    const ts = session.texts_style || {};
    const box = ts[boxKey] || {};
    updateSession('texts_style', boxKey, { ...box, [key]: value });
  };

  // Panneau de fond d'un texte : activer, couleur fond, texte, bord, coins, padding
  const renderTextBox = (boxKey) => {
    const ts = session.texts_style || {};
    const box = ts[boxKey] || {};
    return (
      <>
        <label style={styles.label} >
          <input
            type="checkbox"
            style={{ marginRight: '8px', accentColor: '#00ff88' }}
            checked={!!box.enabled}
            onChange={(e) => updateTextBox(boxKey, 'enabled', e.target.checked)}
          />
          Activer le fond du panneau
        </label>
        {box.enabled && (
          <>
            <label style={styles.label}>Couleur du fond</label>
            <input
              style={styles.colorPicker}
              type="color"
              value={hexColor(box.color, '#1a1a1a')}
              onChange={(e) => updateTextBox(boxKey, 'color', e.target.value)}
            />
            <label style={styles.label}>Couleur du texte (dans le panneau)</label>
            <input
              style={styles.colorPicker}
              type="color"
              value={hexColor(box.text_color, '#FFFFFF')}
              onChange={(e) => updateTextBox(boxKey, 'text_color', e.target.value)}
            />
            <label style={styles.label}>Bordure — couleur</label>
            <input
              style={styles.colorPicker}
              type="color"
              value={hexColor(box.border_color, '#FFFFFF')}
              onChange={(e) => updateTextBox(boxKey, 'border_color', e.target.value)}
            />
            <label style={styles.label}>
              Épaisseur bordure: {(box.border_width || 0)}px
            </label>
            <input
              style={styles.slider}
              type="range"
              min="0"
              max="12"
              value={box.border_width || 0}
              onChange={(e) => updateTextBox(boxKey, 'border_width', parseInt(e.target.value))}
            />
            <label style={styles.label}>
              Coins arrondis: {(box.radius || 0)}px
            </label>
            <input
              style={styles.slider}
              type="range"
              min="0"
              max="60"
              value={box.radius || 0}
              onChange={(e) => updateTextBox(boxKey, 'radius', parseInt(e.target.value))}
            />
            <label style={styles.label}>
              Padding: {(box.padding || 0)}px
            </label>
            <input
              style={styles.slider}
              type="range"
              min="0"
              max="40"
              value={box.padding || 0}
              onChange={(e) => updateTextBox(boxKey, 'padding', parseInt(e.target.value))}
            />
          </>
        )}
      </>
    );
  };

  const exportCodex = () => {
    // Réintègre le clip édité + la session dans le codex multi-clips
    const merged = {
      ...(codex || {}),
      session,
      clips: codex?.clips
        ? [clip, ...(codex.clips || []).slice(1)]
        : [clip],
    };
    const finalCodex = {
      ...merged,
      session: {
        ...session,
        review_mode: activeRanking ? 'ranking_compilation' : activeReveal ? 'reveal_compilation' : reviewMode === 'pur_pack' ? 'pur_pack' : session.review_mode,
        ...(activeRanking ? { ranking: activeRanking } : {}),
        ...(activeReveal ? { reveal: activeReveal } : {}),
        ...(reviewMode === 'pur_pack' && purManifest ? { pur_manifest: purManifest } : {}),
      },
      reveal_manifest: activeReveal || revealManifest || null,
      ranking_manifest: activeRanking || rankingManifest || null,
      pur_manifest: reviewMode === 'pur_pack' ? purManifest : null,
      virtual_sequences: sequences || null,
      validated_by_magos: validated,
    };
    const blob = new Blob([JSON.stringify(finalCodex, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'codex.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const texts = clip.texts || {};
  const textMode = texts.mode || (texts.title ? 'title' : 'none');
  const presets = session.presets || {};
  const background = session.background || {};

  return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <div style={{ fontSize: '18px', fontWeight: 900, letterSpacing: '0.05em' }}>
          LACRIMAE — F03 Preview <span style={{ fontSize: 12, color: '#00ff88' }}>v4 session</span>
        </div>
        <div style={{ fontSize: '13px', color: '#888' }}>
          🖼 {background.image ? background.image : background.color || 'fond'}
          {'  |  '}
          📝 {textMode}
          {'  |  '}
          🎨 {presets.color_preset || 'punchy'}
          {'  |  '}
          🔊 {Math.round((clip.volume ?? 1) * 100)}%
                    {'  | '}
          ⟳ {vidWidth}×{vidHeight}
          {'  | '}
          ⏱️ {(totalFrames / fps).toFixed(1)}s
        </div>
      </div>

      {/* Main layout */}
      <div style={styles.mainLayout}>
        {/* Player */}
        <div style={styles.playerContainer} title="Double-cliquez pour poser le logo ici">
          <div
            style={{ position: 'relative', width: '100%', maxWidth: '300px' }}
            onClick={handleLogoClick}
          >
            <Player
              ref={playerRef}
              component={OmniComposition}
              inputProps={{ codex: clip, videoSrc, session, sequences, hybridManifest: activeHybrid, hybridIntroSrc, musicTimeline: music, revealManifest: activeReveal || activeRanking, purManifest: reviewMode === 'pur_pack' ? purManifest : null }}
              durationInFrames={totalFrames}
              fps={fps}
              compositionWidth={vidWidth}
              compositionHeight={vidHeight}
              style={{
                width: '100%',
                maxWidth: '300px',
                aspectRatio: `${vidWidth} / ${vidHeight}`,
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
              }}
              controls
              autoPlay
              muted={false}
              loop
            />

            {/* Repère + modale de confirmation de la balise logo */}
            {logoPending && (
              <div
                style={{
                  position: 'absolute',
                  left: `${logoPending.x_pct}%`,
                  top: `${logoPending.y_pct}%`,
                  transform: 'translate(-50%, -50%)',
                  zIndex: 30,
                }}
              >
                <div style={{
                  width: '44px', height: '44px', borderRadius: '50%',
                  border: '3px solid #00ff88', backgroundColor: 'rgba(0,0,0,0.4)',
                  boxShadow: '0 0 12px rgba(0,255,136,0.8)',
                  pointerEvents: 'none',
                }} />
              </div>
            )}
            {logoPending && (
              <div style={{
                position: 'absolute', inset: 0, display: 'flex',
                alignItems: 'center', justifyContent: 'center', zIndex: 40,
              }}>
                <div style={{
                  background: '#141414', border: '1px solid #00ff88', borderRadius: '10px',
                  padding: '16px 20px', textAlign: 'center', boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
                  maxWidth: '260px',
                }}>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#e0e0e0', marginBottom: '10px' }}>
                    Poser le logo ici ?
                  </div>
                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                    <button
                      style={{ padding: '8px 20px', background: '#1a3a1a', border: '1px solid #2a5a2a', borderRadius: '8px', color: '#88ff88', cursor: 'pointer', fontWeight: 700 }}
                      onClick={() => confirmLogoPlacement(true)}
                    >
                      Oui
                    </button>
                    <button
                      style={{ padding: '8px 20px', background: '#1a1a1a', border: '1px solid #444', borderRadius: '8px', color: '#aaa', cursor: 'pointer', fontWeight: 700 }}
                      onClick={() => confirmLogoPlacement(false)}
                    >
                      Non
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sequence manifest summary */}
        {sequences?.sequences?.length > 0 && (
          <div style={{ ...styles.panel, maxWidth: '360px', marginBottom: '12px' }}>
            <div style={{ fontWeight: 800, color: '#00ff88', marginBottom: '8px' }}>FAST MATCH CUT — TIMELINE</div>
            <div style={{ color: '#aaa', fontSize: '12px', marginBottom: '8px' }}>
              {sequences.sequences.length} séquences virtuelles · {sequences.cut_interval_frames || 7} frames / cut · source muette
            </div>
            <div style={{ maxHeight: '130px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '11px', color: '#bbb' }}>
              {sequences.sequences.slice(0, 60).map((item, index) => (
                <div key={item.id || index} style={{ padding: '3px 0', borderBottom: '1px solid #222' }}>
                  {String(index + 1).padStart(2, '0')} · {item.id || `seq_${index + 1}`} · source frame {item.source_start_frame} · timeline {item.timeline_start_frame ?? index * (sequences.cut_interval_frames || 7)}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Right panel */}
        <div style={styles.panel}>
          <div style={styles.tabs}>
            <button style={activeTab === 'text' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('text')}>
              📝 Texte
            </button>
            <button style={activeTab === 'hybrid' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('hybrid')}>
              ◈ Hybrid / EGO
            </button>
            <button style={activeTab === 'reveal' ? styles.tabActive : styles.tab} onClick={() => { setActiveTab('reveal'); updateReviewMode('reveal_compilation'); }}>
              ◇ Reveal
            </button>
            <button style={activeTab === 'ranking' ? styles.tabActive : styles.tab} onClick={() => { setActiveTab('ranking'); updateReviewMode('ranking_compilation'); }}>
              # Ranking
            </button>
            <button style={activeTab === 'pur' ? styles.tabActive : styles.tab} onClick={() => { setActiveTab('pur'); if (reviewMode !== 'pur_pack') setSession((s) => ({ ...s, review_mode: 'pur_pack' })); }}>
              ⚡ PUR
            </button>
            <button style={activeTab === 'fond' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('fond')}>
              🖼 Fond & Logo
            </button>
            <button style={activeTab === 'composition' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('composition')}>
              ⟳ Composition
            </button>
            <button style={activeTab === 'video' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('video')}>
              🎬 Vidéo
            </button>
              <button style={activeTab === 'audio' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('audio')}>
                ♪ Audio Sync
              </button>
              <button style={activeTab === 'effects' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('effects')}>
              🎨 Effets
            </button>
            <button style={activeTab === 'sharp' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('sharp')}>
              🔍 Netteté
            </button>
          </div>

          {/* ══════════ RANKING COMPILATION : list-overlay ══════════ */}
          {activeTab === 'ranking' && (() => {
            const gc = rankingManifest?.narrative?.global_controls || {};
            const titleWords = rankingManifest?.narrative?.title_words || [{ text: '', color: '#FFFFFF' }, { text: '', color: '#FFD400' }, { text: '', color: '#FFFFFF' }, { text: '', color: '#FFFFFF' }];
            const updateTitleWord = (wordIndex, patch) => {
              const words = [...titleWords];
              words[wordIndex] = { ...(words[wordIndex] || {}), ...patch };
              updateRankingNarrative('title_words', words);
            };
            const updateGC = (key, value) => updateRankingNarrative('global_controls', { ...(gc), [key]: value });
            return (
              <div style={styles.panelContent}>
                <label style={{ ...styles.label, color: '#ffd400', fontSize: '14px' }}>RANKING COMPILATION</label>
                <div style={{ color: '#aaa', fontSize: 12, lineHeight: 1.45 }}>Liste visible : tous les rangs empilés du bas vers le haut. Clip plein écran. Rang #1 = toujours le dernier.</div>

                {/* ── CONTROLS GLOBAUX ── */}
                <div style={{ marginTop: 8, padding: 8, border: '1px solid #4a4020', borderRadius: 7, background: '#1a1408' }}>
                  <label style={{ ...styles.label, color: '#ffd400', fontSize: 12 }}>🎛️ APPARENCE GÉNÉRALE</label>
                  <div style={{ marginTop: 6 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Taille numéros</span><span style={{ color: '#ffd400' }}>{Number(gc.number_scale ?? 1).toFixed(2)}x</span></label>
                    <input style={styles.slider} type="range" min="0.3" max="3" step="0.05" value={gc.number_scale ?? 1} onChange={(e) => updateGC('number_scale', parseFloat(e.target.value))} />
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Taille écritures</span><span style={{ color: '#ffd400' }}>{Number(gc.label_scale ?? 1).toFixed(2)}x</span></label>
                    <input style={styles.slider} type="range" min="0.3" max="3" step="0.05" value={gc.label_scale ?? 1} onChange={(e) => updateGC('label_scale', parseFloat(e.target.value))} />
                  </div>
                  <label style={{ ...styles.label, display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                    <input type="checkbox" checked={gc.clip_audio !== false} onChange={(e) => updateGC('clip_audio', e.target.checked)} />
                    <span>🔊 Son des clips</span>
                  </label>
                  <div style={{ marginTop: 4 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Espacement</span><span style={{ color: '#ffd400' }}>{gc.list_spacing ?? 2}px</span></label>
                    <input style={styles.slider} type="range" min="-10" max="40" step="1" value={gc.list_spacing ?? 2} onChange={(e) => updateGC('list_spacing', parseFloat(e.target.value))} />
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Liste X %</span><span style={{ color: '#ffd400' }}>{gc.list_x_pct ?? 5}%</span></label>
                    <input style={styles.slider} type="range" min="-50" max="100" step="1" value={gc.list_x_pct ?? 5} onChange={(e) => updateGC('list_x_pct', parseFloat(e.target.value))} />
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Liste Y %</span><span style={{ color: '#ffd400' }}>{gc.list_y_pct ?? 25}%</span></label>
                    <input style={styles.slider} type="range" min="-50" max="100" step="1" value={gc.list_y_pct ?? 25} onChange={(e) => updateGC('list_y_pct', parseFloat(e.target.value))} />
                  </div>
                </div>

                {/* ── TITRE (word-by-word) ── */}
                <div style={{ marginTop: 8, padding: 8, border: '1px solid #4a4020', borderRadius: 7, background: '#1a1408' }}>
                  <label style={{ ...styles.label, color: '#ffd400', fontSize: 12 }}>🎬 TITRE</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 4, marginTop: 4 }}>
                    {[0, 1, 2, 3].map(wi => (
                      <React.Fragment key={wi}>
                        <input style={{ ...styles.input, fontSize: 11 }} value={titleWords[wi]?.text || ''} onChange={(e) => updateTitleWord(wi, { text: e.target.value })} placeholder={wi === 0 ? 'Mot 1' : wi === 1 ? 'Mot 2' : wi === 2 ? 'Mot 3 (opt)' : 'Mot 4 (opt)'} />
                        <input type="color" value={titleWords[wi]?.color || '#FFFFFF'} onChange={(e) => updateTitleWord(wi, { color: e.target.value })} style={{ width: 28, height: 22, border: '1px solid #555', borderRadius: 3, background: 'transparent', cursor: 'pointer' }} />
                      </React.Fragment>
                    ))}
                  </div>
                  <div style={{ marginTop: 6 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Taille titre</span><span style={{ color: '#ffd400' }}>{gc.title_size ?? 42}px</span></label>
                    <input style={styles.slider} type="range" min="20" max="120" step="1" value={gc.title_size ?? 42} onChange={(e) => updateGC('title_size', parseFloat(e.target.value))} />
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Titre X %</span><span style={{ color: '#ffd400' }}>{gc.title_x_pct ?? 50}%</span></label>
                    <input style={styles.slider} type="range" min="0" max="100" step="1" value={gc.title_x_pct ?? 50} onChange={(e) => updateGC('title_x_pct', parseFloat(e.target.value))} />
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <label style={{ ...styles.label, display: 'flex', justifyContent: 'space-between' }}><span>Titre Y %</span><span style={{ color: '#ffd400' }}>{gc.title_y_pct ?? 5}%</span></label>
                    <input style={styles.slider} type="range" min="0" max="100" step="1" value={gc.title_y_pct ?? 5} onChange={(e) => updateGC('title_y_pct', parseFloat(e.target.value))} />
                  </div>
                  <label style={styles.label}>Catégorie</label>
                  <input style={styles.input} value={rankingManifest?.narrative?.category ?? ''} onChange={(e) => updateRankingNarrative('category', e.target.value)} placeholder="ACTION" />
                  <label style={styles.label}>Libellé final</label>
                  <input style={styles.input} value={rankingManifest?.narrative?.final_label ?? ''} onChange={(e) => updateRankingNarrative('final_label', e.target.value)} placeholder="THE GOAT" />
                </div>

                {/* ── RANGS ── */}
                <div style={{ marginTop: 8, paddingTop: 10, borderTop: '1px solid #4a4020' }}>
                  <label style={{ ...styles.label, color: '#ffd400' }}>RANGS</label>
                  {(activeRanking?.entries || rankingManifest?.entries || []).map((entry, index) => {
                    const labelWords = entry.label_words || [];
                    const updateLabelWord = (wordIndex, patch) => {
                      const words = [...labelWords];
                      words[wordIndex] = { ...(words[wordIndex] || {}), ...patch };
                      updateRankingEntry(index, { label_words: words });
                    };
                    const updateEntry = (patch) => updateRankingEntry(index, patch);
                    return (
                      <div key={entry.source_id || index} style={{ marginTop: 8, padding: 9, border: `1px solid ${entry.rank === 1 ? '#8a6820' : '#333'}`, borderRadius: 7, background: entry.rank === 1 ? '#1d1708' : '#111' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: entry.rank === 1 ? '#ffd400' : '#ddd', fontWeight: 800, fontSize: 12 }}>
                          <span>#{entry.rank}{entry.rank === 1 ? ' — 👑 LE ROI' : ''}</span>
                          <span style={{ color: '#888', fontWeight: 500 }}>{entry.source_id}</span>
                        </div>

                        {/* ── NUMÉRO ── */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                          <label style={{ ...styles.label, margin: 0, fontSize: 11 }}>Couleur #</label>
                          <input type="color" value={entry.number_color ?? '#FF4444'} onChange={(e) => updateEntry({ number_color: e.target.value })} style={{ width: 28, height: 22, border: '1px solid #555', borderRadius: 3, background: 'transparent', cursor: 'pointer' }} />
                          <label style={{ ...styles.label, margin: 0, fontSize: 11, marginLeft: 'auto' }}>Taille #</label>
                          <input style={{ ...styles.slider, width: 80 }} type="range" min="12" max="100" step="1" value={entry.number_size ?? 42} onChange={(e) => updateEntry({ number_size: parseFloat(e.target.value) })} />
                          <span style={{ color: '#ffd400', fontSize: 10, minWidth: 24 }}>{entry.number_size ?? 42}</span>
                        </div>

                        {/* ── LABEL (word-by-word) ── */}
                        <div style={{ marginTop: 4 }}>
                          <label style={{ ...styles.label, fontSize: 11 }}>Label (mots + couleurs)</label>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 3 }}>
                            {[0, 1, 2, 3].map(wi => (
                              <React.Fragment key={wi}>
                                <input style={{ ...styles.input, fontSize: 10, minHeight: 22 }} value={labelWords[wi]?.text || ''} onChange={(e) => updateLabelWord(wi, { text: e.target.value })} placeholder={wi === 0 ? 'Mot 1' : wi === 1 ? 'Mot 2' : wi === 2 ? 'Mot 3' : 'Mot 4'} />
                                <input type="color" value={labelWords[wi]?.color || '#FFFFFF'} onChange={(e) => updateLabelWord(wi, { color: e.target.value })} style={{ width: 24, height: 20, border: '1px solid #555', borderRadius: 3, background: 'transparent', cursor: 'pointer' }} />
                              </React.Fragment>
                            ))}
                          </div>
                          <div style={{ marginTop: 4 }}>
                            <label style={{ ...styles.label, fontSize: 10, display: 'flex', justifyContent: 'space-between' }}><span>Taille texte</span><span style={{ color: '#ffd400' }}>{entry.label_size ?? 22}px</span></label>
                            <input style={styles.slider} type="range" min="8" max="80" step="1" value={entry.label_size ?? 22} onChange={(e) => updateEntry({ label_size: parseFloat(e.target.value) })} />
                          </div>
                          <div style={{ marginTop: 4 }}>
                            <label style={{ ...styles.label, fontSize: 10, display: 'flex', justifyContent: 'space-between' }}><span>Position haut %</span><span style={{ color: '#ffd400' }}>{entry.label_y_top ?? 0}%</span></label>
                            <input style={styles.slider} type="range" min="0" max="100" step="1" value={entry.label_y_top ?? 0} onChange={(e) => updateEntry({ label_y_top: parseFloat(e.target.value) })} />
                          </div>
                          <div style={{ marginTop: 4 }}>
                            <label style={{ ...styles.label, fontSize: 10, display: 'flex', justifyContent: 'space-between' }}><span>Position bas %</span><span style={{ color: '#ffd400' }}>{entry.label_y_bottom ?? 50}%</span></label>
                            <input style={styles.slider} type="range" min="0" max="100" step="1" value={entry.label_y_bottom ?? 50} onChange={(e) => updateEntry({ label_y_bottom: parseFloat(e.target.value) })} />
                          </div>
                        </div>

                        {/* ── SFX ── */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, padding: '4px 6px', border: '1px solid #2a2a2a', borderRadius: 5, background: '#0a0a0a' }}>
                          <label style={{ ...styles.label, margin: 0, fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                            <input type="checkbox" checked={Boolean(entry.sfx?.enabled)} onChange={(e) => updateEntry({ sfx: { ...(entry.sfx || {}), enabled: e.target.checked } })} />
                            SFX transition
                          </label>
                          {entry.sfx?.enabled && (
                            <>
                              <input style={{ ...styles.input, fontSize: 10, flex: 1 }} value={entry.sfx?.file || ''} onChange={(e) => updateEntry({ sfx: { ...(entry.sfx || {}), file: e.target.value } })} placeholder="sfx/impact.mp3" />
                              <span style={{ color: '#888', fontSize: 10 }}>Vol</span>
                              <input style={{ ...styles.slider, width: 60 }} type="range" min="0" max="2" step="0.05" value={entry.sfx?.volume ?? 0.8} onChange={(e) => updateEntry({ sfx: { ...(entry.sfx || {}), volume: parseFloat(e.target.value) } })} />
                            </>
                          )}
                        </div>

                        {/* ── TIMING ── */}
                        <label style={{ ...styles.label, fontSize: 11 }}>Durée : {Number(entry.duration_seconds || 3).toFixed(2)} s</label>
                        <input style={styles.slider} type="range" min="0.5" max="10" step="0.1" value={Number(entry.duration_seconds || 3)} onChange={(e) => updateEntry({ duration_seconds: parseFloat(e.target.value) })} />
                        {entry.rank === 1 && <div style={{ color: '#ffd400', fontSize: 10, marginTop: 4 }}>👑 Le roi — apparaît en dernier, du bas vers le haut</div>}
                        {entry.rank !== 1 && <div style={{ color: '#888', fontSize: 10, marginTop: 4 }}>↑ Apparaît du bas vers le haut</div>}
                      </div>
                    );
                  })}
                  {!(activeRanking?.entries?.length || rankingManifest?.entries?.length) && <div style={{ color: '#ff9f66', fontSize: 12, padding: 8 }}>Aucun ranking_manifest.json chargé. F00-F doit d'abord produire le manifeste.</div>}
                </div>
              </div>
            );
          })()}
{/* ══════════ REVEAL COMPILATION : six clips + narratif ══════════ */}
          {activeTab === 'reveal' && (
            <div style={styles.panelContent}>
              <label style={{ ...styles.label, color: '#ffcc66', fontSize: '14px' }}>REVEAL COMPILATION</label>
              <div style={{ color: '#aaa', fontSize: 12, lineHeight: 1.45 }}>
                F00-E prépare les clips. Ici, F03 construit la compilation : textes, ordre, durées, transitions et reveal final.
              </div>
              <label style={styles.label}>Thème</label>
              <input style={styles.input} value={revealManifest?.narrative?.theme ?? ''} onChange={(e) => updateRevealNarrative('theme', e.target.value)} placeholder="CAMOUFLAGE" />
              <label style={styles.label}>Texte OTHERS</label>
              <input style={styles.input} value={revealManifest?.narrative?.others_label ?? ''} onChange={(e) => updateRevealNarrative('others_label', e.target.value)} placeholder="OTHERS" />
              <label style={styles.label}>Texte THIS ONE</label>
              <input style={styles.input} value={revealManifest?.narrative?.this_one_label ?? ''} onChange={(e) => updateRevealNarrative('this_one_label', e.target.value)} placeholder="THIS ONE" />
              <label style={styles.label}>Texte de transition</label>
              <input style={styles.input} value={revealManifest?.narrative?.transition_text ?? ''} onChange={(e) => updateRevealNarrative('transition_text', e.target.value)} placeholder="WAIT FOR THIS ONE" />
              <label style={styles.label}>Texte final</label>
              <input style={styles.input} value={revealManifest?.narrative?.final_text ?? ''} onChange={(e) => updateRevealNarrative('final_text', e.target.value)} placeholder="" />
              <div style={{ marginTop: 8, paddingTop: 10, borderTop: '1px solid #4a3920' }}>
                <label style={{ ...styles.label, color: '#ffcc66' }}>SOURCES ET SCÈNES</label>
                {(activeReveal?.sources || revealManifest?.sources || []).map((source, index) => {
                  const scene = activeReveal?.scenes?.[index] || revealManifest?.scenes?.[index] || {};
                  return (
                    <div key={source.id || index} style={{ marginTop: 8, padding: 9, border: `1px solid ${scene.final_reveal ? '#8a5a28' : '#333'}`, borderRadius: 7, background: scene.final_reveal ? '#1d160e' : '#111' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, color: scene.final_reveal ? '#ffcc66' : '#ddd', fontWeight: 800, fontSize: 12 }}>
                        <span>{scene.final_reveal ? 'THIS ONE — ' : 'OTHER '}{String(index + 1).padStart(2, '0')}</span>
                        <span style={{ color: '#888', fontWeight: 500 }}>{source.file || 'clip non chargé'}</span>
                      </div>
                      <label style={styles.label}>Durée scène : {Number(scene.duration_seconds || source.duration_seconds || 1).toFixed(2)} s</label>
                      <input style={styles.slider} type="range" min="0.5" max="20" step="0.1" value={Number(scene.duration_seconds || source.duration_seconds || 1)} onChange={(e) => updateRevealScene(index, 'duration_seconds', parseFloat(e.target.value))} />
                      <div style={{ display: 'flex', gap: 7, alignItems: 'center', marginTop: 5 }}>
                        <span style={{ color: '#aaa', fontSize: 11, flex: 1 }}>Miroir préparé par F00-E : <b style={{ color: source.mirror ? '#00ff88' : '#888' }}>{source.mirror ? 'OUI' : 'NON'}</b></span>
                        <select style={{ ...styles.select, width: 125 }} value={scene.transition || (index % 2 === 0 ? 'with_sfx' : 'silent')} onChange={(e) => updateRevealScene(index, 'transition', e.target.value)}>
                          <option value="with_sfx">Avec SFX</option>
                          <option value="silent">Silencieuse</option>
                        </select>
                      </div>
                      <select style={{ ...styles.select, marginTop: 6 }} value={scene.motion?.preset || 'none'} onChange={(e) => updateRevealScene(index, 'motion', { ...(scene.motion || {}), preset: e.target.value })}>
                        <option value="none">Mouvement : aucun</option>
                        <option value="drift_left">Mouvement : drift gauche</option>
                        <option value="drift_right">Mouvement : drift droite</option>
                        <option value="drift_up">Mouvement : drift haut</option>
                        <option value="drift_down">Mouvement : drift bas</option>
                      </select>
                    </div>
                  );
                })}
                {!(activeReveal?.sources?.length || revealManifest?.sources?.length) && <div style={{ color: '#ff9f66', fontSize: 12, padding: 8 }}>Aucun pack F00-E chargé. Placez reveal_sources.json et ses clips dans public/.</div>}
              </div>
              <div style={{ marginTop: 8, paddingTop: 10, borderTop: '1px solid #4a3920' }}>
                <label style={{ ...styles.label, color: '#ffcc66' }}>REVEAL FINAL</label>
                <label style={styles.label}>Obscurité : {Math.round(Number((revealManifest?.reveal?.darkness ?? 0.72)) * 100)}%</label>
                <input style={styles.slider} type="range" min="0" max="0.9" step="0.01" value={revealManifest?.reveal?.darkness ?? 0.72} onChange={(e) => updateReveal({ reveal: { ...(revealManifest?.reveal || {}), darkness: parseFloat(e.target.value) } })} />
                <label style={styles.label}>Puissance shake vertical : {revealManifest?.reveal?.shake_power ?? 85}%</label>
                <input style={styles.slider} type="range" min="0" max="100" step="1" value={revealManifest?.reveal?.shake_power ?? 85} onChange={(e) => updateReveal({ reveal: { ...(revealManifest?.reveal || {}), shake_power: parseInt(e.target.value, 10) } })} />
                <label style={styles.label}>Durée du shake : {revealManifest?.reveal?.shake_duration_frames ?? 12} frames</label>
                <input style={styles.slider} type="range" min="3" max="30" step="1" value={revealManifest?.reveal?.shake_duration_frames ?? 12} onChange={(e) => updateReveal({ reveal: { ...(revealManifest?.reveal || {}), shake_duration_frames: parseInt(e.target.value, 10) } })} />
              </div>
            </div>
          )}

          {/* ══════════ PUR : bras armé PERTURABO ══════════ */}
          {activeTab === 'pur' && (() => {
            const purInfo = purManifest?.pur || {};
            const anti = purManifest?.entries?.[0]?.anti_detection || {};
            const overlayLines = purManifest?.narrative?.overlay?.lines || [];
            const hasPack = Boolean(purManifest?.entries?.length);
            return (
              <div style={styles.panelContent}>
                <label style={{ ...styles.label, color: '#66ddff', fontSize: '14px' }}>⚡ MODE PUR — PERTURABO → LACRIMAE</label>
                <div style={{ color: '#aaa', fontSize: 12, lineHeight: 1.45 }}>
                  Pack PUR (production_pack_pur_*.json) → manifeste dev10.pur.v1 → clip plein écran,
                  hook 0-3s (visage, pas de texte), overlay 2 lignes après le hook, zooms frame-exacts, anti-détection.
                </div>

                <div style={{ marginTop: 10, padding: 8, border: '1px solid #1a4a5a', borderRadius: 7, background: '#081820' }}>
                  <label style={{ ...styles.label, color: '#66ddff', fontSize: 12 }}>📥 CHARGER UN PACK PUR</label>
                  <label style={{ ...styles.uploadLabel, marginTop: 8 }}>
                    {purPackRaw ? `Pack chargé : ${purPackRaw.pack_id || '?'} (${purPackRaw.identite?.angle_id || '—'})` : 'Déposer production_pack_pur_*.json (EXPORT PERTURABO)'}
                    <input type="file" accept=".json" style={{ display: 'none' }} onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const reader = new FileReader();
                      reader.onload = () => {
                        try {
                          const pack = JSON.parse(String(reader.result));
                          setPurPackRaw(pack);
                          convertPurPack(pack, purCanvas);
                        } catch (err) {
                          setError('Pack PUR invalide : ' + err.message);
                        }
                      };
                      reader.readAsText(file);
                    }} />
                  </label>
                  {purPackRaw && (
                    <button style={{ ...styles.button, marginTop: 6 }} onClick={() => convertPurPack(purPackRaw, purCanvas)}>
                      ↻ Reconvertir le pack ({purCanvas})
                    </button>
                  )}
                </div>

                <div style={{ marginTop: 10, padding: 8, border: '1px solid #1a4a5a', borderRadius: 7, background: '#081820' }}>
                  <label style={{ ...styles.label, color: '#66ddff', fontSize: 12 }}>🖼️ FORMAT DE SORTIE</label>
                  <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                    {['9:16', '16:9', '1:1'].map((fmt) => (
                      <button key={fmt} style={{ ...(purCanvas === fmt ? styles.tabActive : styles.tab), flex: 1 }}
                        onClick={() => { setPurCanvas(fmt); if (purPackRaw) convertPurPack(purPackRaw, fmt); }}>
                        {fmt}
                      </button>
                    ))}
                  </div>
                </div>

                {hasPack && (
                  <>
                    <div style={{ marginTop: 10, padding: 8, border: '1px solid #1a4a5a', borderRadius: 7, background: '#081820' }}>
                      <label style={{ ...styles.label, color: '#66ddff', fontSize: 12 }}>✍️ OVERLAY (après le hook)</label>
                      {overlayLines.map((line, index) => (
                        <input key={`pur_ol_${index}`} style={{ ...styles.input, marginTop: 6 }} value={line}
                          onChange={(e) => updatePurOverlayLine(index, e.target.value)} />
                      ))}
                      {!overlayLines.length && <div style={{ color: '#ff9f66', fontSize: 12, marginTop: 4 }}>Aucune ligne d'overlay dans le pack.</div>}
                    </div>

                    <div style={{ marginTop: 10, padding: 8, border: '1px solid #1a4a5a', borderRadius: 7, background: '#081820' }}>
                      <label style={{ ...styles.label, color: '#66ddff', fontSize: 12 }}>🛡️ ANTI-DÉTECTION (pack)</label>
                      <div style={{ color: '#ccc', fontSize: 12, marginTop: 4, lineHeight: 1.6 }}>
                        Mirror : {anti.mirror ? '✅ activé' : '—'} · Speed : {anti.speed || 1}x · Crop : {anti.crop_pct || 0}%<br />
                        Hook : {purInfo.hook?.duration_sec ?? 3}s · Zooms : {purManifest?.entries?.[0]?.zooms?.length || 0} · SFX : {purManifest?.entries?.[0]?.sfx_list?.length || 0}<br />
                        Source : {purInfo.platform || '—'} · {purInfo.angle_id || '—'} · {purInfo.generator || '—'}
                      </div>
                    </div>

                    <div style={{ marginTop: 10, padding: 8, border: '1px solid #1a4a5a', borderRadius: 7, background: '#081820' }}>
                      <label style={{ ...styles.label, color: '#66ddff', fontSize: 12 }}>🔗 SOURCE VOD</label>
                      <div style={{ color: '#ccc', fontSize: 11, marginTop: 4, wordBreak: 'break-all' }}>{purInfo.source || '—'}</div>
                      <div style={{ color: '#8ac', fontSize: 11, marginTop: 4 }}>
                        Segment : {purInfo.start_sec ?? '—'}s → {purInfo.end_sec ?? '—'}s<br />
                        Le workflow dev10_pur_render télécharge ce segment (F00-PUR, yt-dlp sections).
                      </div>
                    </div>
                  </>
                )}
                {!hasPack && <div style={{ color: '#ff9f66', fontSize: 12, padding: 8 }}>Aucun pack PUR converti. Dépose un production_pack_pur_*.json ci-dessus (ou place pur_manifest.json dans public/).</div>}
              </div>
            );
          })()}

          {/* ══════════ HYBRID / EGO : mode narratif séparé ══════════ */}
          {activeTab === 'hybrid' && (
            <div style={styles.panelContent}>
              <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>MODE DE REVIEW</label>
              <select
                style={styles.select}
                value={reviewMode}
                onChange={(e) => updateReviewMode(e.target.value)}
              >
                <option value="match_cut">Mode 1 — Match Cut</option>
                <option value="hybrid_narrative">Mode 2 — Hybrid / EGO</option>
              </select>
              {reviewMode === 'hybrid_narrative' && (
                <div style={{ marginTop: '12px', padding: '12px', border: '1px solid #5a4422', borderRadius: '8px', background: '#16120d' }}>
                  <label style={{ ...styles.label, color: '#ffcc66' }}>INTRO — image ou vidéo</label>
                  <input
                    style={styles.input}
                    type="file"
                    accept="video/*,image/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const url = URL.createObjectURL(file);
                      setHybridIntroSrc(url);
                      updateSession('hybrid', 'intro', {
                        ...(session.hybrid?.intro || {}),
                        source: file.name,
                        source_type: file.type.startsWith('image/') ? 'image' : 'video',
                      });
                    }}
                  />
                  <label style={styles.label}>Découpage vidéo (secondes IN / OUT, optionnel)</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input style={{ ...styles.input, width: '50%' }} type="number" min="0" step="0.1" placeholder="IN" value={session.hybrid?.intro?.in_seconds ?? 0} onChange={(e) => updateSession('hybrid', 'intro', { ...(session.hybrid?.intro || {}), in_seconds: parseFloat(e.target.value) || 0 })} />
                    <input style={{ ...styles.input, width: '50%' }} type="number" min="0" step="0.1" placeholder="OUT" value={session.hybrid?.intro?.out_seconds ?? 2} onChange={(e) => updateSession('hybrid', 'intro', { ...(session.hybrid?.intro || {}), out_seconds: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid #4a3920' }}>
                    <label style={{ ...styles.label, color: '#ffcc66' }}>PHRASE FIXE — introduction</label>
                    <label style={styles.label}>Texte fixe</label>
                    <input
                      style={styles.input}
                      value={session.hybrid?.intro_text?.text || "C'EST JUSTE UN JOUEUR"}
                      onChange={(e) => updateSession('hybrid', 'intro_text', { ...(session.hybrid?.intro_text || {}), text: e.target.value })}
                    />
                    <label style={styles.label}>Durée de la phrase</label>
                    <select style={styles.select} value={session.hybrid?.intro_text?.duration_mode || 'until_match_cut'} onChange={(e) => updateSession('hybrid', 'intro_text', { ...(session.hybrid?.intro_text || {}), duration_mode: e.target.value })}>
                      <option value="until_match_cut">Jusqu’au Match Cut</option>
                      <option value="until_end">Jusqu’à la fin</option>
                    </select>
                    <label style={styles.label}>Scale phrase : {(session.hybrid?.intro_text?.scale ?? 1).toFixed(1)}×</label>
                    <input style={styles.slider} type="range" min="0.2" max="10" step="0.1" value={session.hybrid?.intro_text?.scale ?? 1} onChange={(e) => updateSession('hybrid', 'intro_text', { ...(session.hybrid?.intro_text || {}), scale: parseFloat(e.target.value) })} />
                    <label style={styles.label}>Hauteur phrase : {session.hybrid?.intro_text?.position_y ?? 78}%</label>
                    <input style={styles.slider} type="range" min="0" max="100" step="1" value={session.hybrid?.intro_text?.position_y ?? 78} onChange={(e) => updateSession('hybrid', 'intro_text', { ...(session.hybrid?.intro_text || {}), position_y: parseInt(e.target.value, 10) })} />
                    <label style={styles.label}>Angle phrase : {session.hybrid?.intro_text?.rotation_deg ?? 0}°</label>
                    <input style={styles.slider} type="range" min="-180" max="180" value={session.hybrid?.intro_text?.rotation_deg ?? 0} onChange={(e) => updateSession('hybrid', 'intro_text', { ...(session.hybrid?.intro_text || {}), rotation_deg: parseInt(e.target.value, 10) })} />
                    <label style={styles.label}>Couleur phrase</label>
                    <input style={styles.colorPicker} type="color" value={session.hybrid?.intro_text?.color || '#FFFFFF'} onChange={(e) => updateSession('hybrid', 'intro_text', { ...(session.hybrid?.intro_text || {}), color: e.target.value })} />
                  </div>
                  <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid #4a3920' }}>
                    <label style={{ ...styles.label, color: '#ffcc66' }}>EGO — texte d’impact</label>
                    <label style={styles.label}>Texte EGO</label>
                    <input style={styles.input} value={session.hybrid?.ego?.text || 'EGO'} onChange={(e) => updateSession('hybrid', 'ego', { ...(session.hybrid?.ego || {}), text: e.target.value })} />
                    <label style={styles.label}>Durée EGO</label>
                    <select style={styles.select} value={session.hybrid?.ego?.duration_mode || 'until_match_cut'} onChange={(e) => updateSession('hybrid', 'ego', { ...(session.hybrid?.ego || {}), duration_mode: e.target.value })}>
                      <option value="until_match_cut">À partir du Match Cut</option>
                      <option value="until_end">À partir du Match Cut jusqu’à la fin</option>
                    </select>
                    <label style={styles.label}>Scale EGO : {(session.hybrid?.ego?.scale ?? 2).toFixed(1)}×</label>
                    <input style={styles.slider} type="range" min="1" max="10" step="0.1" value={session.hybrid?.ego?.scale ?? 2} onChange={(e) => updateSession('hybrid', 'ego', { ...(session.hybrid?.ego || {}), scale: parseFloat(e.target.value) })} />
                    <label style={styles.label}>Hauteur EGO : {session.hybrid?.ego?.position_y ?? 50}%</label>
                    <input style={styles.slider} type="range" min="0" max="100" step="1" value={session.hybrid?.ego?.position_y ?? 50} onChange={(e) => updateSession('hybrid', 'ego', { ...(session.hybrid?.ego || {}), position_y: parseInt(e.target.value, 10) })} />
                    <label style={styles.label}>Angle EGO : {session.hybrid?.ego?.rotation_deg ?? 0}°</label>
                    <input style={styles.slider} type="range" min="-180" max="180" value={session.hybrid?.ego?.rotation_deg ?? 0} onChange={(e) => updateSession('hybrid', 'ego', { ...(session.hybrid?.ego || {}), rotation_deg: parseInt(e.target.value, 10) })} />
                    <label style={styles.label}>Couleur EGO</label>
                    <input style={styles.colorPicker} type="color" value={session.hybrid?.ego?.color || '#FFFFFF'} onChange={(e) => updateSession('hybrid', 'ego', { ...(session.hybrid?.ego || {}), color: e.target.value })} />
                  </div>
                  <div style={{ marginTop: '12px', padding: '8px', background: '#211b10', border: '1px solid #6b5328', borderRadius: '6px', fontSize: '12px', color: '#ddc58b' }}>
                    En Mode 2, EGO est réservé au Match Cut : il est masqué pendant toute l’introduction et démarre uniquement au hard cut. Les réglages sont immédiats et la tête de lecture conserve sa position.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══════════ AUDIO : musique, boucle et climax ══════════ */}
          {activeTab === 'audio' && (
            <div style={styles.panelContent}>
              <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>AUDIO SYNC</label>
              <input style={styles.input} type="file" accept="audio/*" onChange={(e) => {
                const file = e.target.files?.[0]; if (!file) return;
                const url = URL.createObjectURL(file); setAudioSrc(url);
                updateMusic('enabled', true); updateMusic('audio_file', file.name); updateMusic('audio_src', url);
              }} />
              <label style={styles.label}>Mode de synchronisation</label>
              <select style={styles.select} value={music.sync_mode} onChange={(e) => updateMusic('sync_mode', e.target.value)}>
                <option value="off">Désactivé</option><option value="manual">Manuel</option><option value="assisted">Assisté</option><option value="beat_locked">Verrouillé sur les beats</option>
              </select>
              <label style={styles.label}>Musique : {music.audio_file || 'aucun fichier sélectionné'}</label>
              <audio ref={audioPlayerRef} src={audioSrc || undefined} preload="metadata" onLoadedMetadata={(e) => setAudioDuration(Number.isFinite(e.currentTarget.duration) ? e.currentTarget.duration : 0)} onTimeUpdate={(e) => setAudioPosition(e.currentTarget.currentTime)} onPlay={() => setAudioPlaying(true)} onPause={() => setAudioPlaying(false)} onEnded={() => setAudioPlaying(false)} style={{ display: 'none' }} />
              {audioSrc && <div style={{ margin: '8px 0 10px', padding: 8, background: '#0e1713', border: '1px solid #2d6b50', borderRadius: 6 }}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6 }}>
                  <button type="button" style={styles.smallButton} onClick={() => seekAudio(Math.max(0, audioPosition - 1))}>−1 s</button>
                  <button type="button" style={{ ...styles.smallButton, minWidth: 64 }} onClick={toggleAudioPlayback}>{audioPlaying ? 'Pause' : 'Play'}</button>
                  <button type="button" style={styles.smallButton} onClick={() => audioPlayerRef.current?.pause()}>Stop</button>
                  <button type="button" style={styles.smallButton} onClick={() => seekAudio(audioPosition + 1)}>+1 s</button>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: '#b8ffd9' }}>{audioPosition.toFixed(2)} s / {(audioDuration || waveformDuration).toFixed(2)} s</span>
                </div>
                <input aria-label="Position audio" type="range" min="0" max={audioDuration || waveformDuration} step="0.01" value={Math.min(audioPosition, audioDuration || waveformDuration)} onChange={(e) => seekAudio(parseFloat(e.target.value))} style={styles.slider} />
                <div style={{ fontSize: 10, color: '#8eb5a0' }}>Lecteur indépendant : cette piste ne déplace pas la tête de lecture vidéo.</div>
              </div>}
              {waveform && (
                <div style={{ margin: '8px 0 12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, fontSize: 10, color: '#b8c9c1', marginBottom: 4 }}>
                    <span><b style={{ color: '#00ff88' }}>VERT</b> = boucle intro</span>
                    <span><b style={{ color: '#ff4d6d' }}>ROUGE</b> = partie forte Match Cut</span>
                  </div>
                  <svg
                    ref={waveformRef}
                    viewBox={`0 0 ${waveformWidth} ${waveformHeight}`}
                    preserveAspectRatio="none"
                    style={{ width: '100%', height: 82, background: '#0d1512', border: '1px solid #214b3a', borderRadius: 6, touchAction: 'none', overflow: 'visible' }}
                    onPointerDown={seekAudioFromEvent}
                    onPointerMove={(event) => { if (waveDrag) setWaveHandleTime(waveDrag, waveTimeFromEvent(event)); }}
                    onPointerUp={() => setWaveDrag(null)}
                    onPointerCancel={() => setWaveDrag(null)}
                  >
                    {Array.from({ length: Math.ceil(waveformDuration / 5) + 1 }, (_, index) => index * 5).filter((seconds) => seconds <= waveformDuration).map((seconds) => (
                      <g key={`tick_${seconds}`}>
                        <line x1={waveformX(seconds)} x2={waveformX(seconds)} y1="0" y2={waveformHeight} stroke="#284638" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                        <text x={Math.min(waveformWidth - 20, Math.max(2, waveformX(seconds) + 2))} y="78" fill="#71867b" fontSize="9">{seconds}s</text>
                      </g>
                    ))}
                    <rect x={waveformX(music.intro_in)} y="0" width={Math.max(1, waveformX(music.intro_out) - waveformX(music.intro_in))} height={waveformHeight} fill="#00ff88" opacity="0.18" />
                    <rect x={waveformX(music.match_cut_in)} y="0" width={Math.max(1, waveformX(music.match_cut_out) - waveformX(music.match_cut_in))} height={waveformHeight} fill="#ff4d6d" opacity="0.14" />
                    <polyline points={waveform} fill="none" stroke="#00ff88" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                    <line x1={waveformX(music.intro_in)} x2={waveformX(music.intro_in)} y1="0" y2={waveformHeight} stroke="#00ff88" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                    <line x1={waveformX(music.intro_out)} x2={waveformX(music.intro_out)} y1="0" y2={waveformHeight} stroke="#00ff88" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                    <line x1={waveformX(music.match_cut_in)} x2={waveformX(music.match_cut_in)} y1="0" y2={waveformHeight} stroke="#ff4d6d" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                    <line x1={waveformX(music.match_cut_out)} x2={waveformX(music.match_cut_out)} y1="0" y2={waveformHeight} stroke="#ff4d6d" strokeWidth="2" vectorEffect="non-scaling-stroke" />
                    <line x1={waveformX(music.intro_duration_seconds)} x2={waveformX(music.intro_duration_seconds)} y1="0" y2={waveformHeight} stroke="#c5a8ff" strokeWidth="2" strokeDasharray="5 3" vectorEffect="non-scaling-stroke" />
                    <line x1={waveformX(audioPosition)} x2={waveformX(audioPosition)} y1="0" y2={waveformHeight} stroke="#ffffff" strokeWidth="2" opacity="0.85" vectorEffect="non-scaling-stroke" />
                    <g style={{ cursor: 'ew-resize' }} onPointerDown={(event) => beginWaveDrag(event, 'loop_in')}>
                      <circle cx={waveformX(music.intro_in)} cy="12" r="6" fill="#00ff88" stroke="#07150f" strokeWidth="2" />
                      <text x={Math.min(waveformWidth - 28, Math.max(2, waveformX(music.intro_in) + 5))} y="10" fill="#b8ffd9" fontSize="10" fontWeight="700">IN</text>
                    </g>
                    <g style={{ cursor: 'ew-resize' }} onPointerDown={(event) => beginWaveDrag(event, 'loop_out')}>
                      <circle cx={waveformX(music.intro_out)} cy="12" r="6" fill="#00ff88" stroke="#07150f" strokeWidth="2" />
                      <text x={Math.min(waveformWidth - 28, Math.max(2, waveformX(music.intro_out) - 20))} y="10" fill="#b8ffd9" fontSize="10" fontWeight="700">OUT</text>
                    </g>
                    <g style={{ cursor: 'ew-resize' }} onPointerDown={(event) => beginWaveDrag(event, 'match_cut_in')}>
                      <circle cx={waveformX(music.match_cut_in)} cy={waveformHeight - 20} r="6" fill="#ff4d6d" stroke="#210b12" strokeWidth="2" />
                      <text x={Math.min(waveformWidth - 45, Math.max(2, waveformX(music.match_cut_in) + 7))} y={waveformHeight - 23} fill="#ffb4c3" fontSize="10" fontWeight="700">DROP</text>
                    </g>
                    <g style={{ cursor: 'ew-resize' }} onPointerDown={(event) => beginWaveDrag(event, 'match_cut_out')}>
                      <circle cx={waveformX(music.match_cut_out)} cy={waveformHeight - 20} r="6" fill="#ff4d6d" stroke="#210b12" strokeWidth="2" />
                      <text x={Math.min(waveformWidth - 28, Math.max(2, waveformX(music.match_cut_out) - 18))} y={waveformHeight - 23} fill="#ffb4c3" fontSize="10" fontWeight="700">FIN</text>
                    </g>
                    <text x="4" y={waveformHeight - 3} fill="#71867b" fontSize="9">0s</text>
                    <text x={waveformWidth - 42} y={waveformHeight - 3} fill="#71867b" fontSize="9">{waveformDuration.toFixed(1)}s</text>
                  </svg>
                  <div style={{ marginTop: 5, fontSize: 11, color: '#d4e3dc' }}>
                    Glisse <b style={{ color: '#00ff88' }}>IN</b>/<b style={{ color: '#00ff88' }}>OUT</b> pour choisir la portion répétée de l’introduction, puis <b style={{ color: '#ff4d6d' }}>DROP</b>/<b style={{ color: '#ff4d6d' }}>FIN</b> pour choisir toute la partie forte du Match Cut.
                  </div>
                </div>
              )}
              <label style={styles.label}>Décalage global : {music.offset_frames} frames</label>
              <input style={styles.slider} type="range" min="-30" max="30" step="1" value={music.offset_frames} onChange={(e) => updateMusic('offset_frames', parseInt(e.target.value, 10))} />
              <div style={{ marginTop: 10, padding: 10, background: '#101a15', border: '1px solid #23543e', borderRadius: 6 }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: 13 }}>INTRO — portion à boucler</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input aria-label="Intro IN" style={{ ...styles.input, width: '50%' }} type="number" min="0" step="0.05" value={music.intro_in} onChange={(e) => updateMusicBlock('intro', 'in_seconds', parseFloat(e.target.value) || 0)} />
                  <input aria-label="Intro OUT" style={{ ...styles.input, width: '50%' }} type="number" min="0" step="0.05" value={music.intro_out} onChange={(e) => updateMusicBlock('intro', 'out_seconds', parseFloat(e.target.value) || 0)} />
                </div>
                <div style={{ display: 'flex', gap: 8, fontSize: 11, color: '#9cb9aa' }}><span style={{ width: '50%' }}>Intro IN (s)</span><span style={{ width: '50%' }}>Intro OUT (s)</span></div>
                <label style={styles.label}>Nombre de boucles : {music.loop_count}</label>
                <input style={styles.slider} type="range" min="1" max="20" step="1" value={music.loop_count} onChange={(e) => updateMusicBlock('intro', 'loop_count', parseInt(e.target.value, 10))} />
                <div style={{ fontSize: 11, color: '#b8ffd9' }}>Durée intro calculée : {music.intro_duration_seconds.toFixed(2)} s</div>
                <label style={styles.label}>Volume intro : {Math.round(music.intro_volume * 100)}%</label>
                <input style={styles.slider} type="range" min="0" max="1.5" step="0.05" value={music.intro_volume} onChange={(e) => updateMusicBlock('intro', 'volume', parseFloat(e.target.value))} />
                <label style={styles.label}>Vitesse intro : {music.intro_speed.toFixed(2)}×</label>
                <input style={styles.slider} type="range" min="0.5" max="1.5" step="0.05" value={music.intro_speed} onChange={(e) => updateMusicBlock('intro', 'speed', parseFloat(e.target.value))} />
              </div>
              <div style={{ marginTop: 10, padding: 10, background: '#1a1015', border: '1px solid #6d2941', borderRadius: 6 }}>
                <label style={{ ...styles.label, color: '#ff6a8a', fontSize: 13 }}>MATCH CUT — partie forte</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input aria-label="Match Cut IN" style={{ ...styles.input, width: '50%' }} type="number" min="0" step="0.05" value={music.match_cut_in} onChange={(e) => updateMusicBlock('match_cut', 'in_seconds', parseFloat(e.target.value) || 0)} />
                  <input aria-label="Match Cut OUT" style={{ ...styles.input, width: '50%' }} type="number" min="0" step="0.05" value={music.match_cut_out} onChange={(e) => updateMusicBlock('match_cut', 'out_seconds', parseFloat(e.target.value) || 0)} />
                </div>
                <div style={{ display: 'flex', gap: 8, fontSize: 11, color: '#d8a8b4' }}><span style={{ width: '50%' }}>Drop / IN (s)</span><span style={{ width: '50%' }}>Fin / OUT (s)</span></div>
                <div style={{ fontSize: 11, color: '#ffb4c3' }}>Durée Match Cut : {music.match_cut_duration_seconds.toFixed(2)} s · début vidéo : {music.intro_duration_seconds.toFixed(2)} s</div>
                <label style={styles.label}>Volume Match Cut : {Math.round(music.match_cut_volume * 100)}%</label>
                <input style={styles.slider} type="range" min="0" max="1.5" step="0.05" value={music.match_cut_volume} onChange={(e) => updateMusicBlock('match_cut', 'volume', parseFloat(e.target.value))} />
                <label style={styles.label}>Vitesse Match Cut : {music.match_cut_speed.toFixed(2)}×</label>
                <input style={styles.slider} type="range" min="0.5" max="1.5" step="0.05" value={music.match_cut_speed} onChange={(e) => updateMusicBlock('match_cut', 'speed', parseFloat(e.target.value))} />
              </div>
              <div style={{ marginTop: 10, padding: 10, background: '#15121c', border: '1px solid #49356e', borderRadius: 6 }}>
                <label style={{ ...styles.label, color: '#c5a8ff', fontSize: 13 }}>TRANSITION AUDIO</label>
                <select style={styles.select} value={music.transition.type} onChange={(e) => updateMusicBlock('transition', 'type', e.target.value)}>
                  <option value="beat_cut">Cut sur le beat</option><option value="crossfade">Crossfade court</option><option value="beat_jump">Beat jump</option>
                </select>
                <label style={styles.label}>Durée technique : {music.transition.duration_ms} ms</label>
                <input style={styles.slider} type="range" min="0" max="200" step="5" value={music.transition.duration_ms} onChange={(e) => updateMusicBlock('transition', 'duration_ms', parseInt(e.target.value, 10))} />
                <label style={styles.label}>Alignement</label>
                <select style={styles.select} value={music.transition.alignment} onChange={(e) => updateMusicBlock('transition', 'alignment', e.target.value)}><option value="nearest_beat">Beat le plus proche</option><option value="exact">Position exacte</option></select>
              </div>
              <div style={{ marginTop: 10, padding: 8, background: '#101a15', border: '1px solid #23543e', borderRadius: 6, fontSize: 12, color: '#a7e9c2' }}>
                La Preview calcule automatiquement la fin de l’intro et démarre le Match Cut + EGO à ce moment. La fin de la partie forte reste le champ Match Cut OUT choisi par l’opérateur.
              </div>
            </div>
          )}

          {/* ══════════ COMPOSITION : format, cadrage et rotation ══════════ */}
          {activeTab === 'composition' && (
            <div style={styles.panelContent}>
              <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>FORMAT DE COMPOSITION</label>
              <select style={styles.select} value={composition.preset} onChange={(e) => {
                const p = COMPOSITION_PRESETS[e.target.value];
                setSession((s) => ({
                  ...s,
                  composition: { ...(s.composition || {}), preset: e.target.value, ...(p ? { width: p.width, height: p.height } : {}) },
                }));
              }}>
                {Object.entries(COMPOSITION_PRESETS).map(([key, p]) => <option key={key} value={key}>{p.label}</option>)}
              </select>
              <label style={styles.label}>Mode d’affichage de la source</label>
              <select style={styles.select} value={composition.fit} onChange={(e) => updateComposition('fit', e.target.value)}>
                <option value="cover">Cover — remplir l’écran</option>
                <option value="contain">Contain — garder toute l’image</option>
              </select>
              <label style={styles.label}>Fond de remplissage</label>
              <select style={styles.select} value={composition.background_fill} onChange={(e) => updateComposition('background_fill', e.target.value)}>
                <option value="blurred_video">Vidéo agrandie et floutée</option>
                <option value="solid">Couleur du fond</option>
                <option value="none">Aucun fond</option>
              </select>
              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>POSITION ET ÉCHELLE DE LA VIDÉO</label>
                <label style={styles.label}>Zoom : {(composition.video_scale ?? 1).toFixed(2)}×</label>
                <input style={styles.slider} type="range" min="1" max="7" step="0.05" value={composition.video_scale ?? 1} onChange={(e) => updateComposition('video_scale', parseFloat(e.target.value))} />
                <label style={styles.label}>Position horizontale : {composition.video_position_x ?? 0}%</label>
                <input style={styles.slider} type="range" min="-100" max="100" step="1" value={composition.video_position_x ?? 0} onChange={(e) => updateComposition('video_position_x', parseInt(e.target.value))} />
                <label style={styles.label}>Position verticale : {composition.video_position_y ?? 0}%</label>
                <input style={styles.slider} type="range" min="-100" max="100" step="1" value={composition.video_position_y ?? 0} onChange={(e) => updateComposition('video_position_y', parseInt(e.target.value))} />
              </div>
              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>ROTATION DE LA VIDÉO</label>
                <select style={styles.select} value={composition.rotation_mode} onChange={(e) => updateComposition('rotation_mode', e.target.value)}>
                  <option value="static">Fixe — angle opérateur</option>
                  <option value="none">Aucune</option>
                  <option value="per_sequence">Par séquence</option>
                  <option value="continuous">Continue</option>
                </select>
                {composition.rotation_mode === 'static' && <>
                  <label style={styles.label}>Angle fixe : {composition.rotation_deg ?? 0}°</label>
                  <input style={styles.slider} type="range" min="-360" max="360" step="1" value={composition.rotation_deg ?? 0} onChange={(e) => updateComposition('rotation_deg', parseInt(e.target.value))} />
                  <input style={{ ...styles.input, marginTop: '4px' }} type="number" min="-360" max="360" step="1" value={composition.rotation_deg ?? 0} onChange={(e) => updateComposition('rotation_deg', parseInt(e.target.value) || 0)} />
                </>}
                {composition.rotation_mode === 'per_sequence' && <>
                  <label style={styles.label}>Degrés ajoutés par séquence : {composition.rotation_step_deg}°</label>
                  <input style={styles.slider} type="range" min="0" max="15" step="0.5" value={composition.rotation_step_deg} onChange={(e) => updateComposition('rotation_step_deg', parseFloat(e.target.value))} />
                </>}
                {composition.rotation_mode === 'continuous' && <>
                  <label style={styles.label}>Rotation totale : {composition.rotation_total_deg}°</label>
                  <input style={styles.slider} type="range" min="0" max="360" step="1" value={composition.rotation_total_deg} onChange={(e) => updateComposition('rotation_total_deg', parseInt(e.target.value))} />
                  <label style={styles.label}>Sens de rotation</label>
                  <select style={styles.select} value={composition.rotation_direction} onChange={(e) => updateComposition('rotation_direction', parseInt(e.target.value))}>
                    <option value="1">Horaire</option><option value="-1">Antihoraire</option>
                  </select>
                </>}
                {composition.rotation_mode !== 'none' && <>
                  <label style={styles.label}>Calque affecté</label>
                  <select style={styles.select} value={composition.rotation_layer} onChange={(e) => updateComposition('rotation_layer', e.target.value)}>
                    <option value="video">Vidéo uniquement</option><option value="composition">Composition entière</option>
                  </select>
                </>}
              </div>
            </div>
          )}

          {/* ══════════ TEXTE : mode titre / titre+paragraphe ══════════ */}
          {activeTab === 'text' && (
            <div style={styles.panelContent}>
              <label style={styles.label}>Mode texte</label>
              <select
                style={styles.select}
                value={textMode}
                onChange={(e) => {
                  const mode = e.target.value;
                  if (mode === 'dark_luxury_flash_text') {
                    const content = texts.content || texts.title || 'TO IS HIM';
                    updateTexts('mode', mode);
                    updateTexts('content', content);
                    updateFlashUnits(buildFlashUnits(content, texts.units || []));
                    setFlashSelectedIndex(0);
                  } else {
                    updateTexts('mode', mode);
                  }
                }}
              >
                <option value="title">Titre seul</option>
                <option value="title+paragraph">Titre + paragraphe</option>
                <option value="dark_luxury_flash_text">Dark Luxury Flash Text</option>
                <option value="none">Aucun texte</option>
              </select>

              {textMode === 'dark_luxury_flash_text' ? (
                <>
                  <label style={styles.label}>Phrase Flash Text — affichage mot par mot</label>
                  <textarea
                    style={{ ...styles.input, minHeight: '70px', resize: 'vertical', fontFamily: 'inherit' }}
                    value={texts.content || ''}
                    placeholder="TO IS HIM"
                    onChange={(e) => {
                      const content = e.target.value;
                      updateTexts('content', content);
                      updateFlashUnits(buildFlashUnits(content, texts.units || []));
                      setFlashSelectedIndex(0);
                    }}
                  />
                  <div style={{ margin: '8px 0', color: '#aaa', fontSize: '12px' }}>
                    Un seul mot à l’écran. Double-cliquez sur un mot pour le passer en rouge.
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                    {(texts.units || buildFlashUnits(texts.content || texts.title || '', [])).map((unit, index) => (
                      <button
                        key={unit.id || index}
                        type="button"
                        onClick={() => setFlashSelectedIndex(index)}
                        onDoubleClick={() => updateFlashUnit(index, { impact: !unit.impact })}
                        style={{
                          ...styles.button,
                          padding: '7px 9px',
                          color: unit.impact ? '#FF0000' : '#FFFFFF',
                          border: index === flashSelectedIndex ? '1px solid #00ff88' : '1px solid #444',
                        }}
                      >
                        {String(unit.text || '').toUpperCase()}
                      </button>
                    ))}
                  </div>
                  {(() => {
                    const units = texts.units || buildFlashUnits(texts.content || texts.title || '', []);
                    const unit = units[flashSelectedIndex] || units[0];
                    if (!unit) return null;
                    return (
                      <div style={{ padding: '10px', background: '#17100f', border: '1px solid #6b2424', borderRadius: '8px' }}>
                        <label style={styles.label}>Mot sélectionné : {String(unit.text).toUpperCase()}</label>
                        <label style={styles.label}>Durée : {unit.duration_frames ?? 8} frames</label>
                        <input style={styles.slider} type="range" min="1" max="120" value={unit.duration_frames ?? 8} onChange={(e) => updateFlashUnit(flashSelectedIndex, { duration_frames: parseInt(e.target.value, 10) })} />
                        <label style={styles.label}>Rotation : {unit.rotation_deg ?? 0}°</label>
                        <input style={styles.slider} type="range" min="-180" max="180" value={unit.rotation_deg ?? 0} onChange={(e) => updateFlashUnit(flashSelectedIndex, { rotation_deg: parseInt(e.target.value, 10) })} />
                        <label style={styles.label}>Scale : {(unit.scale ?? 1).toFixed(1)}×</label>
                        <input style={styles.slider} type="range" min="1" max="10" step="0.1" value={unit.scale ?? 1} onChange={(e) => updateFlashUnit(flashSelectedIndex, { scale: parseFloat(e.target.value) })} />
                        <label style={styles.label}>Flou à l’apparition : {unit.blur_frames ?? 0} frames</label>
                        <input style={styles.slider} type="range" min="0" max="3" value={unit.blur_frames ?? 0} onChange={(e) => updateFlashUnit(flashSelectedIndex, { blur_frames: parseInt(e.target.value, 10) })} />
                      </div>
                    );
                  })()}
                </>
              ) : (
                <>
                  <label style={styles.label}>Titre (haut)</label>
                  <input style={styles.input} type="text" value={texts.title || ''} onChange={(e) => updateTexts('title', e.target.value)} />
                  <label style={styles.label}>Position titre (haut): {(texts.title_offset_pct ?? 8)}%</label>
                  <input style={styles.slider} type="range" min="2" max="30" value={texts.title_offset_pct ?? 8} onChange={(e) => updateTexts('title_offset_pct', parseInt(e.target.value))} />
                  {(textMode === 'title+paragraph') && (
                    <>
                      <label style={styles.label}>Paragraphe (bas, 4 lignes max)</label>
                      <textarea style={{ ...styles.input, minHeight: '80px', resize: 'vertical', fontFamily: 'inherit' }} value={texts.paragraph || ''} onChange={(e) => updateTexts('paragraph', e.target.value)} />
                      <label style={styles.label}>Position paragraphe (bas): {(texts.paragraph_offset_pct ?? 8)}%</label>
                      <input style={styles.slider} type="range" min="2" max="30" value={texts.paragraph_offset_pct ?? 8} onChange={(e) => updateTexts('paragraph_offset_pct', parseInt(e.target.value))} />
                    </>
                  )}
                </>
              )}

              {/* Style global des textes (session) */}
              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                  🎨 Style global des textes (tous les clips)
                </label>

                <label style={styles.label}>Police</label>
                <select
                  style={styles.select}
                  value={(session.texts_style || {}).font || 'Impact, Arial Black, sans-serif'}
                  onChange={(e) => updateSessionTextsStyle('font', e.target.value)}
                >
                  <option value="Impact, Arial Black, sans-serif">Impact</option>
                  <option value="Arial Black, sans-serif">Arial Black</option>
                  <option value="Bebas Neue, sans-serif">Bebas Neue</option>
                  <option value="Helvetica, sans-serif">Helvetica</option>
                </select>

                <label style={styles.label}>
                  Taille titre: {(session.texts_style || {}).size_title || 96}px
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="40"
                  max="180"
                  value={(session.texts_style || {}).size_title || 96}
                  onChange={(e) => updateSessionTextsStyle('size_title', parseInt(e.target.value))}
                />

                <label style={styles.label}>
                  Taille paragraphe: {(session.texts_style || {}).size_paragraph || 44}px
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="20"
                  max="80"
                  value={(session.texts_style || {}).size_paragraph || 44}
                  onChange={(e) => updateSessionTextsStyle('size_paragraph', parseInt(e.target.value))}
                />

                <label style={styles.label}>Couleur texte</label>
                <input
                  style={styles.colorPicker}
                  type="color"
                  value={(session.texts_style || {}).color || '#FFFFFF'}
                  onChange={(e) => updateSessionTextsStyle('color', e.target.value)}
                />

                <label style={styles.label}>Contour</label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max="8"
                  value={(session.texts_style || {}).stroke_width || 4}
                  onChange={(e) => updateSessionTextsStyle('stroke_width', parseInt(e.target.value))}
                />
              </div>

              {/* Panneaux de fond : TITRE et PARAGRAPHE séparés */}
              {textMode !== 'none' && (
                <>
                  {/* ── Panneau TITRE ── */}
                  <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                    <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                      📦 Panneau du TITRE
                    </label>
                    {renderTextBox('title_box')}
                    <div style={{ marginTop: '6px', fontSize: '11px', color: '#777' }}>
                      Fond actif → les effets texte (contour, ombre) s'annulent automatiquement.
                    </div>
                  </div>

                  {/* ── Panneau PARAGRAPHE ── */}
                  {textMode === 'title+paragraph' && (
                    <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                      <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                        📦 Panneau du PARAGRAPHE
                      </label>
                      {renderTextBox('paragraph_box')}
                      <div style={{ marginTop: '6px', fontSize: '11px', color: '#777' }}>
                        Fond actif → les effets texte s'annulent automatiquement.
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ══════════ FOND & LOGO : menu déroulant des PNG + taille logo ══════════ */}
          {activeTab === 'fond' && (
            <div style={styles.panelContent}>
              <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                🖼 FOND (dossier public/backgrounds/)
              </label>
              <select
                style={styles.select}
                value={background.image || 'solid'}
                onChange={(e) => {
                  const v = e.target.value;
                  updateSession('background', 'image', v === 'solid' ? null : v);
                }}
              >
                <option value="solid">Couleur unie</option>
                {backgrounds.map((bg) => (
                  <option key={bg} value={bg}>🖼 {bg}</option>
                ))}
              </select>
              {backgrounds.length === 0 && (
                <div style={{ fontSize: '12px', color: '#666' }}>
                  Aucun PNG trouvé — déposez vos fonds dans <code>public/backgrounds/</code>
                </div>
              )}

              {background.image ? (
                <>
                  <label style={styles.label}>
                    Échelle du fond: {(background.scale ?? 1).toFixed(2)}x
                  </label>
                  <input
                    style={styles.slider}
                    type="range"
                    min="0.8"
                    max="2"
                    step="0.05"
                    value={background.scale ?? 1}
                    onChange={(e) => updateSession('background', 'scale', parseFloat(e.target.value))}
                  />
                </>
              ) : (
                <>
                  <label style={styles.label}>Couleur de fond</label>
                  <input
                    style={styles.colorPicker}
                    type="color"
                    value={background.color || '#0a0a0a'}
                    onChange={(e) => updateSession('background', 'color', e.target.value)}
                  />
                </>
              )}

              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                  🏷 LOGO (placement ajustable — en haut sous la vidéo par défaut)
                </label>
                <label style={styles.label}>Position du logo</label>
                <select
                  style={styles.select}
                  value={(session.logo || {}).position || 'top_center'}
                  onChange={(e) => updateSession('logo', 'position', e.target.value)}
                >
                  <option value="top_center">Haut — centré</option>
                  <option value="top_left">Haut — gauche</option>
                  <option value="top_right">Haut — droite</option>
                  <option value="bottom_center">Bas — centré</option>
                  <option value="bottom_left">Bas — gauche</option>
                  <option value="bottom_right">Bas — droite</option>
                  <option value="custom">Personnalisé (double-clic)</option>
                </select>
                <div style={{ marginTop: '4px', padding: '8px', background: '#0f2a1a', borderRadius: '8px', fontSize: '12px', color: '#88ff88' }}>
                  💡 <strong>Astuce :</strong> double-cliquez directement sur la vidéo à l'endroit
                  voulu → « Poser le logo ici ? » → Oui. Le logo se place là (coordonnées %).
                  La taille reste ajustable ci-dessous.
                </div>
                <label style={styles.label}>
                  Taille du logo: {(session.logo || {}).width_pct || 20}%
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="5"
                  max="90"
                  value={(session.logo || {}).width_pct || 20}
                  onChange={(e) => updateSession('logo', 'width_pct', parseInt(e.target.value))}
                />
                <label style={styles.label}>
                  Opacité: {Math.round(((session.logo || {}).opacity ?? 1) * 100)}%
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round(((session.logo || {}).opacity ?? 1) * 100)}
                  onChange={(e) => updateSession('logo', 'opacity', parseInt(e.target.value) / 100)}
                />
                <div style={{ marginTop: '8px', padding: '8px', background: '#1a1a1a', borderRadius: '8px', fontSize: '12px', color: '#888' }}>
                  Placez <code>logo.png</code> dans <code>public/</code>. Position, taille
                  et opacité sont réglables en direct.
                </div>
              </div>
            </div>
          )}

          {/* ══════════ VIDÉO : centrage vertical (session, tous les clips) ══════════ */}
          {activeTab === 'video' && (
            <div style={styles.panelContent}>
              <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                🎬 VIDÉO — centrage vertical
              </label>
              <label style={styles.label}>
                Position verticale: {((session.video || {}).offset_y ?? 0) > 0 ? '+' : ''}
                {((session.video || {}).offset_y ?? 0)}%
              </label>
              <input
                style={styles.slider}
                type="range"
                min="-20"
                max="20"
                step="0.5"
                value={(session.video || {}).offset_y ?? 0}
                onChange={(e) => updateSession('video', 'offset_y', parseFloat(e.target.value))}
              />
              <div style={{ marginTop: '8px', padding: '8px', background: '#1a1a1a', borderRadius: '8px', fontSize: '12px', color: '#888' }}>
                Réglage appliqué à tous les clips (session). <strong>+</strong> = vers le bas,
                <strong> −</strong> = vers le haut. Les particularités vidéo s'ajouteront ici.
              </div>
              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #333' }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>MOTION SLOW — INTERPOLATION</label>
                <label style={styles.label}>Activation</label>
                <select style={styles.select} value={motionSlow.enabled ? motionSlow.mode : 'off'} onChange={(e) => {
                  const mode = e.target.value;
                  updateSession('motion_slow', 'enabled', mode !== 'off');
                  updateSession('motion_slow', 'mode', mode);
                }}>
                  <option value="off">Désactivé — Normal</option>
                  <option value="partial">Partiel — plages choisies</option>
                  <option value="global">Global — toute la vidéo</option>
                </select>
                {motionSlow.enabled && <>
                  <label style={styles.label}>Vitesse : {motionSlow.speed}×</label>
                  <select style={styles.select} value={motionSlow.speed} onChange={(e) => updateSession('motion_slow', 'speed', parseFloat(e.target.value))}>
                    <option value="0.75">0,75×</option>
                    <option value="0.5">0,5×</option>
                    <option value="0.25">0,25×</option>
                  </select>
                  {motionSlow.mode === 'partial' && <>
                    <label style={styles.label}>Plages en secondes (ex. 3-7,8-9)</label>
                    <input style={styles.input} type="text" value={motionSlow.ranges || ''} placeholder="3-7" onChange={(e) => updateSession('motion_slow', 'ranges', e.target.value)} />
                  </>}
                  <label style={styles.label}>Moteur</label>
                  <select style={styles.select} value={motionSlow.engine} onChange={(e) => updateSession('motion_slow', 'engine', e.target.value)}>
                    <option value="ffmpeg_minterpolate">FFmpeg — minterpolate</option>
                    <option value="rife_ncnn" disabled>RIFE ncnn — futur moteur qualité (bientôt)</option>
                  </select>
                </>}
                <div style={{ marginTop: '8px', padding: '8px', background: '#0f2a1a', borderRadius: '8px', fontSize: '12px', color: '#88ff88' }}>
                  F00-C est optionnelle. Le mode Normal ne lance aucun traitement d’interpolation.
                </div>
              </div>
            </div>
          )}

          {/* ══════════ EFFETS : colorimétrie par segment en Mode 2 ══════════ */}
          {activeTab === 'effects' && (
            <div style={styles.panelContent}>
              <label style={styles.label}>
                {reviewMode === 'hybrid_narrative' ? 'Color preset — Match Cut uniquement' : 'Color preset — Mode 1'}
              </label>
              {reviewMode === 'hybrid_narrative' && (
                <div style={{ marginBottom: '12px', padding: '8px', background: '#0f2a1a', border: '1px solid #2a6b45', borderRadius: '7px', fontSize: '12px', color: '#9cffc3' }}>
                  En Mode 2, les effets colorimétriques, grain et vignette commencent au hard cut et ne touchent pas l’introduction.
                </div>
              )}
              <select
                style={styles.select}
                value={presets.color_preset || 'punchy'}
                onChange={(e) => {
                  const preset = e.target.value;
                  const filters = {
                    warm_vibrant: 'contrast(1.2) saturate(1.15) brightness(1.05) hue-rotate(3deg)',
                    cold_desaturated: 'contrast(1.1) saturate(0.6) brightness(0.95) hue-rotate(-10deg)',
                    high_contrast: 'contrast(1.5) saturate(1.3) brightness(1.0)',
                    punchy: 'contrast(1.3) saturate(1.5) brightness(1.1)',
                    sepia_soft: 'sepia(0.3) contrast(1.1) saturate(0.9) brightness(1.05)',
                    dark_luxury_noir: 'contrast(1.3) saturate(0.32) brightness(0.96)',
                    scifi_neon_hdr: 'contrast(1.35) saturate(1.45) brightness(0.97)',
                  };
                  setSession((s) => ({
                    ...s,
                    presets: {
                      ...(s.presets || {}),
                      color_preset: preset,
                      color_css_filter: filters[preset] || '',
                      dark_luxury_noir: {
                        enabled: preset === 'dark_luxury_noir',
                        intensity: preset === 'dark_luxury_noir'
                          ? (s.presets?.dark_luxury_noir?.intensity ?? 100)
                          : 0,
                      },
                      scifi_neon_hdr: {
                        enabled: preset === 'scifi_neon_hdr',
                        intensity: preset === 'scifi_neon_hdr'
                          ? (s.presets?.scifi_neon_hdr?.intensity ?? 100)
                          : 0,
                      },
                    },
                  }));
                }}
              >
                <option value="warm_vibrant">Warm Vibrant</option>
                <option value="cold_desaturated">Cold Desaturated</option>
                <option value="high_contrast">High Contrast</option>
                <option value="punchy">Punchy</option>
                <option value="sepia_soft">Sepia Soft</option>
                <option value="dark_luxury_noir">Dark Luxury Noir</option>
                <option value="scifi_neon_hdr">Sci-Fi Neon HDR</option>
              </select>

              <label style={styles.label}>
                Dark Luxury Noir : {presets.dark_luxury_noir?.enabled ? `${presets.dark_luxury_noir.intensity ?? 0}%` : 'désactivé'}
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0"
                max="100"
                step="1"
                value={presets.dark_luxury_noir?.enabled ? (presets.dark_luxury_noir.intensity ?? 0) : 0}
                onChange={(e) => {
                  const intensity = parseInt(e.target.value, 10);
                  setSession((s) => ({
                    ...s,
                    presets: {
                      ...(s.presets || {}),
                      color_preset: intensity > 0 ? 'dark_luxury_noir' : (s.presets?.color_preset || 'punchy'),
                      dark_luxury_noir: { enabled: intensity > 0, intensity },
                      scifi_neon_hdr: { ...(s.presets?.scifi_neon_hdr || {}), enabled: false },
                    },
                  }));
                }}
              />
              <div style={{ margin: '6px 0 12px', padding: '8px', background: '#241b12', border: '1px solid #80652c', borderRadius: '8px', fontSize: '12px', color: '#e5c77b' }}>
                Un seul réglage : noir profond, monochrome chaud, accents champagne/bronze, rouge/violet sélectifs et halo lumineux. La valeur est exportée dans le codex pour PICTOR.
              </div>

              <label style={styles.label}>
                Sci-Fi Neon HDR : {presets.scifi_neon_hdr?.enabled ? `${presets.scifi_neon_hdr.intensity ?? 0}%` : 'désactivé'}
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0"
                max="100"
                step="1"
                value={presets.scifi_neon_hdr?.enabled ? (presets.scifi_neon_hdr.intensity ?? 0) : 0}
                onChange={(e) => {
                  const intensity = parseInt(e.target.value, 10);
                  setSession((s) => ({
                    ...s,
                    presets: {
                      ...(s.presets || {}),
                      color_preset: intensity > 0 ? 'scifi_neon_hdr' : (s.presets?.color_preset || 'punchy'),
                      scifi_neon_hdr: { enabled: intensity > 0, intensity },
                      dark_luxury_noir: { ...(s.presets?.dark_luxury_noir || {}), enabled: false },
                    },
                  }));
                }}
              />
              <div style={{ margin: '6px 0 12px', padding: '8px', background: '#0b2028', border: '1px solid #159bb3', borderRadius: '8px', fontSize: '12px', color: '#7deaff' }}>
                Un seul réglage : noirs profonds, cyan électrique, vert néon et rouge/orange saturés. La valeur est exportée dans le codex pour PICTOR.
              </div>

              <label style={styles.label}>
                Contraste: {(presets.contrast ?? 1.3).toFixed(2)}x
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0.5"
                max="2"
                step="0.05"
                value={presets.contrast ?? 1.3}
                onChange={(e) => updatePreset('contrast', parseFloat(e.target.value))}
              />
              <label style={styles.label}>
                Luminosité: {(presets.brightness ?? 1.1).toFixed(2)}x
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0.5"
                max="2"
                step="0.05"
                value={presets.brightness ?? 1.1}
                onChange={(e) => updatePreset('brightness', parseFloat(e.target.value))}
              />

              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #333' }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                  🔊 Audio + Coup brutal
                </label>
                <label style={styles.label}>
                  Volume: {Math.round((clip.volume ?? 1) * 100)}%
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max="100"
                  value={Math.round((clip.volume ?? 1) * 100)}
                  onChange={(e) => updateClip('volume', parseInt(e.target.value) / 100)}
                />
                <label style={styles.label}>
                  Coup brutal toutes les:{' '}
                  {clip.brutal_cut_interval_frames ? (clip.brutal_cut_interval_frames / fps).toFixed(1) + 's' : 'désactivé'}
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max="12"
                  step="0.5"
                  value={(clip.brutal_cut_interval_frames || 0) / fps}
                  onChange={(e) => updateClip('brutal_cut_interval_frames', Math.round(parseFloat(e.target.value) * fps))}
                />
              </div>

              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #333' }}>
                <label style={{ ...styles.label, color: '#00ff88', fontSize: '14px' }}>
                  ⏩ Slow Motion + Shake
                </label>
                <label style={styles.label}>
                  Cut start: {((clip.slowmo_start_frame || 0) / fps).toFixed(1)}s
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max={totalFrames}
                  step={fps}
                  value={clip.slowmo_start_frame || 0}
                  onChange={(e) => updateClip('slowmo_start_frame', parseInt(e.target.value))}
                />
                <label style={styles.label}>
                  Vitesse: {Math.round((clip.slowmo_speed || 1) * 100)}%
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="10"
                  max="100"
                  value={Math.round((clip.slowmo_speed || 1) * 100)}
                  onChange={(e) => updateClip('slowmo_speed', parseInt(e.target.value) / 100)}
                />
                <label style={styles.label}>
                  Puissance du shake: {clip.shake_power || 0}%
                </label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max="100"
                  value={clip.shake_power || 0}
                  onChange={(e) => updateClip('shake_power', parseInt(e.target.value))}
                />
              </div>

              <label style={styles.label}>
                <input
                  type="checkbox"
                  checked={presets.enhance_4k || false}
                  onChange={(e) => updatePreset('enhance_4k', e.target.checked)}
                  style={{ marginRight: '8px' }}
                />
                  Enhance 4K — segment actif
              </label>
            </div>
          )}

          {/* ══════════ NETTETÉ : sharpening, grain, vignette (session) ══════════ */}
          {activeTab === 'sharp' && (
            <div style={styles.panelContent}>
              <label style={styles.label}>
                Sharpening: {presets.sharpening || 0}%
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0"
                max="100"
                value={presets.sharpening || 0}
                onChange={(e) => updatePreset('sharpening', parseInt(e.target.value))}
              />
              <label style={styles.label}>
                Débruitage: {presets.denoising || 0}%
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0"
                max="100"
                value={presets.denoising || 0}
                onChange={(e) => updatePreset('denoising', parseInt(e.target.value))}
              />
              <label style={styles.label}>
                Grain: {Math.round((presets.grain_intensity || 0) * 100)}%
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0"
                max="100"
                value={Math.round((presets.grain_intensity || 0) * 100)}
                onChange={(e) => updatePreset('grain_intensity', parseInt(e.target.value) / 100)}
              />
              <label style={styles.label}>
                Vignette: {Math.round((presets.vignette || 0) * 100)}%
              </label>
              <input
                style={styles.slider}
                type="range"
                min="0"
                max="100"
                value={Math.round((presets.vignette || 0) * 100)}
                onChange={(e) => updatePreset('vignette', parseInt(e.target.value) / 100)}
              />
              <div style={{ marginTop: '12px', padding: '10px', background: '#1a1a1a', borderRadius: '8px', fontSize: '12px', color: '#888' }}>
                <strong style={{ color: '#00ff88' }}>Global :</strong>
                <br />Ces effets s'appliquent à TOUTE la scène (fond + vidéo + textes + logo)
                — c'est le calque presets au-dessus de tout.
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div style={styles.actions}>
            <button style={styles.exportBtn} onClick={exportCodex}>
              ⬇ Télécharger codex.json
            </button>
            <button
              style={validated ? styles.validatedBtn : styles.validateBtn}
              onClick={() => {
                setValidated(true);
                setClip({ ...clip, validated_by_magos: true });
              }}
            >
              {validated ? '✓ Validé — codex.json prêt (bouton export)' : '✓ Valider le montage'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Styles ── */
const styles = {
  app: { background: '#0a0a0a', color: '#e0e0e0', fontFamily: 'system-ui, -apple-system, sans-serif', minHeight: '100vh', display: 'flex', flexDirection: 'column' },
  loading: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: '#0a0a0a', color: '#888', fontFamily: 'system-ui, sans-serif' },
  header: { padding: '12px 20px', borderBottom: '1px solid #222', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' },
  mainLayout: { display: 'flex', flexDirection: 'row', flex: 1, gap: '20px', padding: '20px', alignItems: 'flex-start' },
  playerContainer: { display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 },
  panel: { width: '340px', minWidth: '300px', maxHeight: '85vh', overflowY: 'auto', background: '#141414', borderRadius: '12px', border: '1px solid #222', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' },
  tabs: { display: 'flex', gap: '4px', marginBottom: '8px', flexWrap: 'wrap' },
  tab: { flex: 1, padding: '8px 12px', background: '#1a1a1a', border: '1px solid #222', borderRadius: '8px', color: '#888', cursor: 'pointer', fontSize: '13px', fontWeight: 600, minWidth: '70px' },
  tabActive: { flex: 1, padding: '8px 12px', background: '#2a2a2a', border: '1px solid #00ff88', borderRadius: '8px', color: '#00ff88', cursor: 'pointer', fontSize: '13px', fontWeight: 600, minWidth: '70px' },
  smallButton: { padding: '5px 8px', background: '#17271f', border: '1px solid #3b805d', borderRadius: '5px', color: '#b8ffd9', cursor: 'pointer', fontSize: '11px', fontWeight: 700 },
  panelContent: { display: 'flex', flexDirection: 'column', gap: '6px' },
  label: { fontSize: '13px', color: '#aaa', fontWeight: 600, marginTop: '4px' },
  input: { padding: '8px 10px', background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', color: '#e0e0e0', fontSize: '14px', outline: 'none' },
  select: { padding: '8px 10px', background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', color: '#e0e0e0', fontSize: '14px', outline: 'none', cursor: 'pointer' },
  slider: { width: '100%', accentColor: '#00ff88', cursor: 'pointer' },
  colorPicker: { width: '100%', height: '36px', border: '1px solid #333', borderRadius: '6px', cursor: 'pointer', background: '#1a1a1a' },
  actions: { marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' },
  exportBtn: { padding: '10px 16px', background: '#1a1a2a', border: '1px solid #2a2a4a', borderRadius: '8px', color: '#88aaff', cursor: 'pointer', fontSize: '14px', fontWeight: 600 },
  validateBtn: { padding: '10px 16px', background: '#1a2a1a', border: '1px solid #2a4a2a', borderRadius: '8px', color: '#88ff88', cursor: 'pointer', fontSize: '14px', fontWeight: 700 },
  validatedBtn: { padding: '10px 16px', background: '#2a4a2a', border: '1px solid #4a8a4a', borderRadius: '8px', color: '#aaffaa', cursor: 'default', fontSize: '14px', fontWeight: 700 },
};

/* Convertit une couleur (hex ou rgba) en hex pour les <input type=color> */
function hexColor(color, fallback) {
  if (!color) return fallback;
  if (/^#[0-9a-fA-F]{6}$/.test(color)) return color;
  const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (m) {
    const toHex = (n) => parseInt(n, 10).toString(16).padStart(2, '0');
    return `#${toHex(m[1])}${toHex(m[2])}${toHex(m[3])}`;
  }
  return fallback;
}
