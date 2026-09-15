/* ═══════════════════════════════════════════════════════════════════
   PurPackComposition — Mode PUR (packs PERTURABO → dev10.pur.v1)

   v2 TEXTE (décision Warsmith 2026-09-10 — PUR_TEXT_IMPLEMENTATION.md) :
     - texte STATIQUE du début à la fin, au même endroit (plus de hook
       sans texte, plus de pop_in) — règle hook ABROGÉE
     - auto-fit : chaque ligne tient sur UNE ligne visuelle (taille
       réduite si débordement, min lisible), max 3 lignes
     - casse mixte (uppercase forcé supprimé, toggle opérateur)
     - boîte à coins arrondis + padding (fond existant)
     - blur : position verticale de la vidéo nette = curseur opérateur
   Miroir exact dans F03_PICTOR (F04) — parité par construction.
   ═══════════════════════════════════════════════════════════════════ */
import React, { useMemo } from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig, Video } from 'remotion';
import { antiDetectionTransform, antiDetectionSpeed } from './antiDetection';
import { normalizePurOverlayParams, normalizePurStyleParams } from './bridgeClipper';
import {
  buildCaviarTimeline,
  caviarPunchScaleAtFrame,
  caviarFlashOpacityAtFrame,
} from './caviarRender';
import caviarBudget from './data/caviar_budget.json';

/**
 * Swell continu (décision Warsmith 2026-09-12) — PAS un zoom :
 * montée douce → tenue légère → redescente douce jusqu'à 1.0, en UNE
 * seule courbe continue. Zéro discontinuité, zéro retour instantané.
 * Champs asset (optionnels) : hold_frames, release_frames, scale_from, scale_to.
 */
function purEaseInOut(t) {
  const x = Math.min(1, Math.max(0, t));
  return x * x * (3 - 2 * x);
}

function purZoomAtFrame(zooms, frame) {
  let scale = 1;
  for (const z of zooms || []) {
    const start = Number(z.moment_frame || 0);
    const attack = Math.max(1, Number(z.frames || 3));
    const hold = Math.max(0, Number(z.hold_frames || 0));
    const release = Math.max(1, Number(z.release_frames || Math.round(attack * 1.5)));
    if (frame >= start && frame < start + attack + hold + release) {
      const peak = Number(z.scale_to ?? 1.06);
      const from = Number(z.scale_from ?? 1);
      let s;
      if (frame < start + attack) {
        s = from + (peak - from) * purEaseInOut((frame - start) / attack);
      } else if (frame < start + attack + hold) {
        s = peak;
      } else {
        s = peak + (1 - peak) * purEaseInOut((frame - start - attack - hold) / release);
      }
      scale *= s;
    }
  }
  return scale;
}

/**
 * Flash blanc de transition (décision Warsmith 2026-09-12) :
 * montée + redescente symétriques, 5 frames par défaut.
 * Déclenché par entry.zooms[].white_flash === true (frontière de segment).
 */
function purWhiteFlashAtFrame(zooms, frame) {
  let opacity = 0;
  for (const z of zooms || []) {
    if (z.white_flash !== true && z.white_flash !== 'true') continue;
    const start = Number(z.moment_frame || 0);
    const f = Math.max(1, Number(z.frames || 5));
    const attack = Math.max(1, Math.round(f / 2));
    const release = Math.max(1, f - attack);
    const peak = Number(z.flash_opacity ?? 1);
    if (frame >= start && frame < start + attack) {
      opacity = Math.max(opacity, peak * ((frame - start) / attack));
    } else if (frame >= start + attack && frame < start + attack + release) {
      opacity = Math.max(opacity, peak * (1 - (frame - start - attack) / release));
    }
  }
  return Math.min(1, Math.max(0, opacity));
}

/** Crop offset depuis anti_detection.crop_pct (2.5% des bords). */
function purCropTransform(cropPct) {
  if (!cropPct) return '';
  const s = 1 + 2 * (cropPct / 100);
  return `scale(${s.toFixed(4)})`;
}

/** '#RRGGBB' + opacité 0-1 → 'rgba(r,g,b,a)'. */
function withAlpha(hex, alpha) {
  const m = String(hex || '').match(/^#?([0-9a-f]{6})$/i);
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${Number(alpha ?? 1).toFixed(3)})`;
}

/** Mesure la largeur d'un texte en px pour une police/taille donnée. */
const measureCtx = typeof document !== 'undefined'
  ? document.createElement('canvas').getContext('2d')
  : null;
function measureTextWidth(text, font) {
  if (!measureCtx) return 0;
  measureCtx.font = font;
  return measureCtx.measureText(text).width;
}

/**
 * Auto-fit : taille uniforme pour toutes les lignes afin que la PLUS LONGUE
 * tienne dans la largeur utile (92 % du canvas). Ne fait que réduire,
 * jamais agrandir. Max 3 lignes affichées.
 */
function fitOverlayLines(lines, baseSize, fontFamily, canvasWidth, minSize) {
  const list = (lines || []).slice(0, 3).map((l) => String(l));
  if (!measureCtx || !canvasWidth || list.length === 0) return { lines: list, size: baseSize };
  const usable = canvasWidth * 0.92;
  const font = `900 ${baseSize}px ${fontFamily}`;
  const widest = Math.max(...list.map((l) => measureTextWidth(l, font)));
  if (widest <= usable) return { lines: list, size: baseSize };
  const fitted = Math.max(Number(minSize || 28), Math.floor(baseSize * (usable / widest)));
  return { lines: list, size: fitted };
}

/** Police embarquée (parité preview/rendu CI) — chargée une seule fois. */
let purFontLoaded = false;
function ensurePurFont() {
  if (purFontLoaded || typeof document === 'undefined') return;
  purFontLoaded = true;
  const face = new FontFace('Montserrat', 'url(/fonts/Montserrat-ExtraBold.ttf)', { weight: '900' });
  face.load().then((f) => document.fonts.add(f)).catch(() => {});
}

export function PurPackComposition({ purManifest, session: sessionProp, entryIndex = 0 }) {
  ensurePurFont();
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width: canvasWidth } = useVideoConfig();
  const manifest = purManifest || sessionProp?.pur || {};
  // MULTI-VIDÉOS : chaque entrée = 1 vidéo finale (A01, A02…). L'aperçu
  // affiche l'entrée sélectionnée ; le style/texte sont GLOBAUX.
  const entries = Array.isArray(manifest.entries) ? manifest.entries : [];
  const safeIndex = Math.max(0, Math.min(Number(entryIndex) || 0, Math.max(0, entries.length - 1)));
  const entry = entries[safeIndex] || {};
  const isMulti = entries.length > 1;
  // Overlay : GLOBAL prioritaire (édité en live) ; copie par entrée en repli
  // (rendu standalone d'un manifeste par pack sans bloc global).
  const globalOverlay = manifest.narrative?.overlay || {};
  const entryOverlay = entry.overlay || {};
  const overlayRaw = {
    ...entryOverlay,
    ...globalOverlay,
    lines: (globalOverlay.lines?.length ? globalOverlay.lines : entryOverlay.lines) || [],
    style_params: { ...(entryOverlay.style_params || {}), ...(globalOverlay.style_params || {}) },
  };
  const overlay = { ...overlayRaw, ...normalizePurOverlayParams(overlayRaw.style_params) };
  const pur = manifest.pur || {};

  const styleName = String(manifest.style || '');
  const styleLayout = styleName === 'blur' ? 'blur'
    : styleName === 'split_scene' ? 'split'
    : styleName === 'reframing' ? 'reframing'
    : 'fullscreen';
  const sp = normalizePurStyleParams(manifest.style_params, styleName || 'blur');

  const localFrame = frame;
  // FIX 2026-09-12 (run 34683747939) : le clip DOIT passer par staticFile()
  // comme tous les autres moteurs (ranking/reveal/hybrid). Le chemin brut
  // produit une URL hors serveur Remotion en CI -> 404 -> delayRender
  // "Loading <Html5Video> duration" jamais resolu -> rendu mort.
  const videoUrl = entry.clip_file ? staticFile(entry.clip_file.replace(/^\.?\//, '')) : null;

  // Anti-detection
  const anti = entry.anti_detection || {};
  const speed = Number(anti.speed || 1);

  // Interrupteurs operateur (workflow, 2026-09-12) — isolation SANS toucher aux assets :
  // fx_mode=off -> AUCUN effet d'echelle (zooms asset, swell, breathing_zoom) : clip normal.
  //   Miroir, crop et speed anti-detection restent appliques (decision Warsmith).
  // mute_bg=true -> style blur : seule la couche nette porte la voix (les 2 couches sonores
  //   decalees simulaient une course/echo de l'audio). Flash blanc de transition : TOUJOURS actif.
  const fxOptions = manifest.fx_options || {};
  const fxOff = fxOptions.fx_mode === 'off';
  const muteBg = fxOptions.mute_bg === true;

  // GROUPE 3 — HEISENBERG : rendu narratif caviar (jump cuts, punch-ins,
  // B-roll numéroté, ducking). Bloc caviar de l'ENTRÉE (rendu CI = 1 vidéo,
  // chaque pack porte ses décisions) avec repli bloc racine (pack mono v1).
  // Absent partout → timeline vide, rendu historique à l'identique.
  const caviarRaw = entry.caviar ?? manifest.caviar;
  const caviar = useMemo(
    () => buildCaviarTimeline(caviarRaw, caviarBudget, {
      fps, speed, durationInFrames, fxOff,
    }),
    [caviarRaw, fps, speed, durationInFrames, fxOff],
  );
  const jumpSegments = caviar.segments; // [] si inactif
  const caviarPunchScale = caviarPunchScaleAtFrame(caviar.punchins, localFrame);
  const caviarFlash = caviarFlashOpacityAtFrame(caviar.flashes, localFrame);
  const caviarBroll = (caviar.brolls || []).find(
    (b) => localFrame >= b.frame && localFrame < b.frame + b.frames,
  );

  const antiTransform = [
    fxOff ? (anti.mirror ? 'scaleX(-1)' : undefined) : antiDetectionTransform(anti, frame, fps),
    purCropTransform(anti.crop_pct),
  ].filter(Boolean).join(' ');

  // Zooms ponctuels (brutal_impact / snap_zoom) — desactives en fx_mode=off
  const zoomScale = fxOff ? 1 : purZoomAtFrame(entry.zooms, localFrame);
  const whiteFlash = purWhiteFlashAtFrame(entry.zooms, localFrame);

  // v2 : texte STATIQUE — visible du début à la fin (static_text !== false),
  // sinon comportement legacy (après le hook). Pas d'animation.
  const staticText = overlay.static_text !== false;
  const overlayVisible = staticText
    ? overlayRaw.lines?.length > 0
    : frame >= Number(overlayRaw.visible_from_frame ?? Math.round(3 * fps)) && overlayRaw.lines?.length > 0;

  // Texte overlay : valeurs éditoriales (fallback legacy color/accent/font_size/outline)
  const lineColors = [overlay.line1_color || overlayRaw.color || '#FFFFFF', overlay.line2_color || overlayRaw.accent || '#FFD700'];
  const fontFamilyBase = overlay.font_family || overlayRaw.fallback_font || 'Arial Black, Impact';
  const uppercase = overlay.uppercase === true;
  const outlineWidth = Number(overlay.outline_width ?? 3);
  const outlineColor = overlay.outline_color || overlayRaw.outline || '#000000';
  const textX = Number(overlay.x_pct ?? 50);
  const textY = Number(overlay.y_pct ?? 22);
  const splitTextSize = styleLayout === 'split' ? Number(sp.text_size ?? overlay.size ?? 68) : Number(overlay.size ?? 68);
  const splitTextX = styleLayout === 'split' ? Number(sp.text_x_pct ?? textX) : textX;
  const splitTextY = styleLayout === 'split' ? Number(sp.text_y_pct ?? textY) : textY;

  // Auto-fit (1 ligne = 1 ligne visuelle)
  const fitted = useMemo(() => fitOverlayLines(
    overlayRaw.lines, splitTextSize, `900 ${splitTextSize}px "${fontFamilyBase}"`,
    canvasWidth || 1080, overlay.min_size,
  ), [overlayRaw.lines, splitTextSize, fontFamilyBase, canvasWidth, overlay.min_size]);
  const renderLines = overlay.auto_fit === false ? (overlayRaw.lines || []).slice(0, 3) : fitted.lines;
  const renderSize = overlay.auto_fit === false ? splitTextSize : fitted.size;

  // Boîte (coins arrondis + padding)
  const bgEnabled = overlay.bg_enabled === true;
  const boxRadius = Number(overlay.box_radius ?? 10);
  const boxPadding = Number(overlay.box_padding ?? 14);
  const bgStyle = bgEnabled
    ? {
        background: withAlpha(overlay.bg_color || '#000000', overlay.bg_opacity ?? 0.65),
        borderRadius: boxRadius,
        padding: `${Math.round(boxPadding * 0.6)}px ${boxPadding}px`,
      }
    : {};

  const videoProps = {
    src: videoUrl,
    // FIX 2026-09-12 (gel ~14s sur A03) : l'ancien startFrom = localFrame*speed DOUBLAIT
    // l'avance (seek + progression ~ 2,1x) -> 30s de contenu epuisees en ~14,6s de
    // timeline, video gelee + voix compresse. Remotion avance SEUL depuis startFrom=0.
    startFrom: 0,
    muted: false, // VOIX DU CLIP ON — décision Warsmith 2026-09-11 (codex : « voix claire » hook)
    playbackRate: speed,
  };
  // GROUPE 3 : si des jump cuts caviar sont actifs, CHAQUE tuile lit la bonne
  // portion source (startFrom en frames). Sans caviar : comportement historique
  // (startFrom=0, lecture continue) — l'audio reste synchronisé car la voix est
  // portée par la vidéo elle-même.
  if (jumpSegments.length > 0) {
    const tile = jumpSegments.find((s) => localFrame >= s.from && localFrame < s.from + s.duration) || jumpSegments[jumpSegments.length - 1];
    videoProps.startFrom = tile.sourceStart + (localFrame - tile.from);
  }

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', overflow: 'hidden' }}>
      {/* MULTI-VIDÉOS : bannière discrète « vidéo X/N » pendant l'aperçu */}
      {isMulti && (
        <div style={{ position: 'absolute', right: 14, bottom: 14, zIndex: 50, pointerEvents: 'none', padding: '4px 10px', borderRadius: 6, background: 'rgba(0,0,0,0.55)', color: '#00ff88', fontSize: 13, fontWeight: 800, letterSpacing: '0.06em' }}>
          VIDÉO {safeIndex + 1}/{entries.length} · {entry.angle_id || entry.source_id || '?'}
        </div>
      )}
      {/* GROUPE 3 — SFX des B-rolls caviar : UNIQUEMENT à l'entrée (règle
          Warsmith anti-saturation), couplé au flash sur la même frame. */}
      {(caviarBroll ? [caviarBroll] : []).map((b, i) => (
        <Sequence key={`caviar_sfx_${b.frame}_${i}`} from={b.frame} durationInFrames={Math.max(1, durationInFrames - b.frame)}>
          <Audio src={staticFile(`sfx/${String(b.sfx) === 'boom' ? 'impact' : b.sfx}.mp3`)} volume={0.55} />
        </Sequence>
      ))}

      {/* GROUPE 3 — Smash audio caviar : le ducking (caviarDuckVolumeAtFrame)
          multipliera le volume musical au climax. La couche musicale PUR
          n'existe pas encore — la fonction est prête et testée, le bloc
          s'activera dès qu'une piste musicale sera branchée ici. */}

      {/* SFX des zooms (volume 50-60% sous la voix) */}
      {(manifest.sfx_available === true ? entry.sfx_list || [] : []).map((sfx, index) => (
        Math.abs(frame - Number(sfx.moment_frame || 0)) < 1 && sfx.type ? (
          <Sequence key={`pur_sfx_${index}`} from={Number(sfx.moment_frame || 0)} durationInFrames={Math.max(1, durationInFrames - Number(sfx.moment_frame || 0))}>
            <Audio src={staticFile(`sfx/${String(sfx.type) === 'boom' ? 'impact' : sfx.type}.mp3`)} volume={Number(sfx.volume ?? 0.55)} />
          </Sequence>
        ) : null
      ))}

      <AbsoluteFill
        style={{
          transform: [antiTransform, `scale(${(zoomScale * caviarPunchScale).toFixed(4)})`].filter((t) => !t.includes('scale(1)') || t !== 'scale(1.0000)').join(' '),
          transformOrigin: 'center center',
        }}
      >
        {/* GROUPE 3 — B-roll numéroté : plein cadre, voix du clip continue,
            flash blanc à l'ENTRÉE (rendu plus bas) + SFX sur la même frame. */}
        {caviarBroll && (
          <Video
            src={staticFile(String(caviarBroll.file).replace(/^\.?\//, ''))}
            startFrom={0}
            muted
            style={{ width: '100%', height: '100%', objectFit: 'cover', zIndex: 5 }}
          />
        )}
        {videoUrl ? (
          styleLayout === 'blur' ? (
            /* ── BLUR : couche arrière floutée + couche avant nette positionnable ── */
            <>
              <Video {...videoProps} muted={muteBg}
                style={{ width: '100%', height: '100%', objectFit: 'cover', filter: `blur(${Number(sp.degree || 24)}px) brightness(0.6)`, transform: `scale(${(Number(sp.bg_scale || 118) / 100).toFixed(4)})` }} />
              <div style={{ position: 'absolute', left: 0, right: 0, top: `${Number(sp.fg_y_pct ?? 62)}%`, height: `${Number(sp.fg_scale || 72)}%`, transform: 'translateY(-50%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Video {...videoProps}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', boxShadow: '0 12px 48px rgba(0,0,0,0.65)' }} />
              </div>
            </>
          ) : styleLayout === 'split' ? (
            /* ── SPLIT : vidéo en haut (top_scale%) + élément bas (bottom_scale%) ── */
            <>
              <div style={{ position: 'absolute', left: 0, top: 0, width: '100%', height: `${Number(sp.top_scale || 62)}%`, overflow: 'hidden' }}>
                <Video {...videoProps}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
              <div style={{ position: 'absolute', left: 0, top: `${Number(sp.top_scale || 62)}%`, width: '100%', height: `${Number(sp.bottom_scale || 38)}%`, background: 'linear-gradient(180deg, #0a0a12 0%, #050505 100%)', borderTop: '2px solid rgba(255,255,255,0.12)' }} />
            </>
          ) : styleLayout === 'reframing' ? (
            /* ── REFRAMING : recadrage scale + offset X/Y ── */
            <Video {...videoProps}
              style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${(Number(sp.scale || 130) / 100).toFixed(4)}) translate(${Number(sp.offset_x_pct || 0)}%, ${Number(sp.offset_y_pct || 0)}%)` }} />
          ) : (
            /* ── FULLSCREEN (ranking / style inconnu) : clip plein écran ── */
            <Video {...videoProps}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          )
        ) : (
          <div style={{ color: '#ff8866', fontSize: 40, textAlign: 'center', alignSelf: 'center' }}>
            CLIP PUR MANQUANT — lance F00-PUR (f00_pur.py)
          </div>
        )}
      </AbsoluteFill>

      {/* Flash blanc de transition (décision Warsmith 2026-09-12) — sous le texte */}
      {whiteFlash > 0 && (
        <AbsoluteFill style={{ backgroundColor: '#FFFFFF', opacity: whiteFlash, pointerEvents: 'none' }} />
      )}

      {/* GROUPE 3 — Flash blanc caviar : ENTRÉE de B-roll UNIQUEMENT (jamais
          à la sortie — spec CAVIAR §1), au-dessus du B-roll, sous le texte. */}
      {caviarFlash > 0 && (
        <AbsoluteFill style={{ backgroundColor: '#FFFFFF', opacity: caviarFlash, pointerEvents: 'none', zIndex: 6 }} />
      )}

      {/* Overlay titre PUR : STATIQUE du début à la fin (v2) — pas d'animation */}
      {overlayVisible && (
        <AbsoluteFill style={{ pointerEvents: 'none' }}>
          <div
            style={{
              position: 'absolute',
              left: `${splitTextX}%`,
              top: `${splitTextY}%`,
              maxWidth: '92%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              gap: 4,
              transform: 'translateX(-50%)',
            }}
          >
            {renderLines.map((line, index) => (
              <div
                key={`pur_line_${index}`}
                style={{
                  fontFamily: `"${fontFamilyBase}", sans-serif`,
                  fontSize: renderSize,
                  fontWeight: 900,
                  lineHeight: 1.12,
                  textTransform: uppercase ? 'uppercase' : 'none',
                  color: lineColors[index] || lineColors[0],
                  WebkitTextStroke: outlineWidth > 0 ? `${outlineWidth}px ${outlineColor}` : undefined,
                  paintOrder: 'stroke fill',
                  textShadow: outlineWidth > 0 ? undefined : '0 2px 12px rgba(0,0,0,0.5)',
                  ...bgStyle,
                  whiteSpace: 'nowrap',
                }}
              >
                {line}
              </div>
            ))}
          </div>
        </AbsoluteFill>
      )}

      {/* Outro : fade_to_black final */}
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
