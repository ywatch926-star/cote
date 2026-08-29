import React, { useState, useEffect, useRef } from 'react';
import { Player } from '@remotion/player';
import { OmniComposition } from './preview/OmniComposition';
import { COMPOSITION_PRESETS, getCompositionConfig } from './preview/compositionConfig';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [validated, setValidated] = useState(false);
  const [activeTab, setActiveTab] = useState('text');
  const [flashSelectedIndex, setFlashSelectedIndex] = useState(0);
  const [logoPending, setLogoPending] = useState(null); // {x_pct, y_pct} balise double-clic
  const playerRef = useRef(null);
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
  const totalFrames = sequences?.total_frames || clip.video?.total_frames || 300;
  const composition = getCompositionConfig(clip, session);
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
              inputProps={{ codex: clip, videoSrc, session, sequences }}
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
              muted
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
            <button style={activeTab === 'fond' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('fond')}>
              🖼 Fond & Logo
            </button>
            <button style={activeTab === 'composition' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('composition')}>
              ⟳ Composition
            </button>
            <button style={activeTab === 'video' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('video')}>
              🎬 Vidéo
            </button>
            <button style={activeTab === 'effects' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('effects')}>
              🎨 Effets
            </button>
            <button style={activeTab === 'sharp' ? styles.tabActive : styles.tab} onClick={() => setActiveTab('sharp')}>
              🔍 Netteté
            </button>
          </div>

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

          {/* ══════════ EFFETS : presets globaux (session) ══════════ */}
          {activeTab === 'effects' && (
            <div style={styles.panelContent}>
              <label style={styles.label}>Color preset (global)</label>
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
                Enhance 4K (global)
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
