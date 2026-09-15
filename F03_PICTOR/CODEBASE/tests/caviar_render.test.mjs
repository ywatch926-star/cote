/* ═══════════════════════════════════════════════════════════════════
   Tests GROUPE 3 — moteur de rendu narratif caviar (caviarRender.js)
   Exécution : node tests/caviar_render.test.mjs   (ou npm run test:caviar)
   Aucun MP4 requis — fonctions pures.
   ═══════════════════════════════════════════════════════════════════ */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test, runSuite } from './harness.mjs';

import {
  normalizeCaviarBlock,
  verifyCaviarBudget,
  enforceCaviarBudget,
  buildCaviarTimeline,
  caviarPunchScaleAtFrame,
  caviarFlashOpacityAtFrame,
  caviarDuckVolumeAtFrame,
} from '../src/caviarRender.js';

const budget = JSON.parse(readFileSync(new URL('../src/data/caviar_budget.json', import.meta.url), 'utf8'));

const emptyBlock = { enabled: true, jump_cuts: [], punchins: [], brolls: [], smash_audio: [] };

/* ── Budget d'Attention (double barrage, côté rendu) ── */

test('budget : pack conforme → vert', () => {
  const events = {
    brolls: [{ at_sec: 8 }], smash_audio: [{ at_sec: 20 }],
    punchins: [{ at_sec: 5 }, { at_sec: 15 }], jump_cuts: [{}, {}, {}, {}, {}],
  };
  const v = verifyCaviarBudget(events, budget);
  assert.equal(v.ok, true);
  assert.equal(v.spend_units, 37); // 12+8+12+5
  assert.equal(v.breathing_units, 63);
});

test('budget : dépense > 55 u → rouge avec raison', () => {
  const events = {
    brolls: [{}, {}, {}], smash_audio: [{}, {}], punchins: [{}, {}, {}, {}], jump_cuts: [],
  };
  const v = verifyCaviarBudget(events, budget);
  assert.equal(v.ok, false);
  assert.equal(v.spend_units, 76);
  assert.ok(v.reasons.some((r) => r.includes('dépense')));
});

test('budget : cap dépassé → rouge', () => {
  const v = verifyCaviarBudget({ brolls: [{}, {}, {}, {}], smash_audio: [], punchins: [], jump_cuts: [] }, budget);
  assert.equal(v.ok, false);
  assert.ok(v.reasons.some((r) => r.includes('cap broll')));
});

/* ── Double barrage : dépôt des excédents ── */

test('barrage : cap broll → dépose les plus TARDIFS', () => {
  const block = { ...emptyBlock, brolls: [{ at_sec: 2, file: 'a' }, { at_sec: 9, file: 'b' }, { at_sec: 15, file: 'c' }, { at_sec: 22, file: 'd' }] };
  const { applied, dropped, gate } = enforceCaviarBudget(block, budget);
  assert.equal(applied.brolls.length, 3);
  assert.ok(!applied.brolls.some((b) => b.at_sec === 22));
  assert.equal(dropped.length, 1);
  assert.equal(gate.ok, true);
});

test('barrage : dépense excédentaire → les plus CHERS déposés en premier', () => {
  const block = {
    ...emptyBlock,
    brolls: [{ at_sec: 3, file: 'a' }, { at_sec: 9, file: 'b' }, { at_sec: 15, file: 'c' }],
    smash_audio: [{ at_sec: 10 }, { at_sec: 20 }, { at_sec: 25 }],
    punchins: [{ at_sec: 4 }, { at_sec: 6 }, { at_sec: 12 }, { at_sec: 18 }],
  };
  // initial 84u ; cap smash → 76u ; brolls déposés (les plus chers) jusqu'à ≤ 55u → 52u
  const { applied, gate, dropped } = enforceCaviarBudget(block, budget);
  assert.equal(gate.ok, true);
  assert.equal(gate.spend_units, 52);
  assert.equal(applied.brolls.length, 1);
  assert.equal(applied.smash_audio.length, 2);
  assert.equal(applied.punchins.length, 4);
  assert.equal(dropped.length, 3);
  assert.ok(dropped.every((d) => d.kind === 'brolls' || d.kind === 'smash_audio'));
});

/* ── Jump cuts : segments timeline↔source ── */

test('timeline inerte si bloc absent/désactivé (zéro régression)', () => {
  for (const raw of [undefined, null, {}, { enabled: false, jump_cuts: [{ cut_at_sec: 5, removes_sec: 1 }] }]) {
    const t = buildCaviarTimeline(raw, budget, { fps: 30, durationInFrames: 900 });
    assert.equal(t.enabled, false);
    assert.deepEqual(t.segments, []);
  }
});

test('jump cut : 2 tuiles contiguës couvrant TOUTE la durée', () => {
  // silence 9→10 s retiré : la source vivante avant la coupe = 9 s = 270 frames
  const block = { ...emptyBlock, jump_cuts: [{ cut_at_sec: 10, removes_sec: 1 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.enabled, true);
  assert.equal(t.segments.length, 2);
  assert.deepEqual(t.segments[0], { from: 0, duration: 270, sourceStart: 0 });
  assert.deepEqual(t.segments[1], { from: 270, duration: 630, sourceStart: 300 });
  assert.equal(t.removed_sec, 1);
  const total = t.segments.reduce((s, x) => s + x.duration, 0);
  assert.equal(total, 900, 'aucun trou, aucun débordement');
});

test('mapping source→timeline cohérent avec les segments', () => {
  const block = { ...emptyBlock, jump_cuts: [{ cut_at_sec: 10, removes_sec: 1 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  // début du silence (9 s) = frontière de tuile ; après la coupe : 11 s → 300
  assert.equal(t.sourceToTimelineFrame(9), 270);
  assert.equal(t.sourceToTimelineFrame(11), 300);
  assert.equal(t.sourceToTimelineFrame(0), 0);
  const seg = t.segments.find((s) => s.from === t.sourceToTimelineFrame(9));
  assert.ok(seg, 'le début du silence tombe sur une frontière de tuile');
});

test('événement DANS un silence retiré → recalé au point de coupe', () => {
  // silence 9→10 s (cut_at_sec=10, removes_sec=1) ; un B-roll à 9,5 s tombe
  // DEDANS : il est recalé sur la frontière de coupe (frame 270), pas perdu.
  const block = { ...emptyBlock, jump_cuts: [{ cut_at_sec: 10, removes_sec: 1 }], brolls: [{ at_sec: 9.5, file: 'b.mp4', numero: 1 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.brolls[0].frame, 270);
  // après la coupe : source 10,5 s → (10,5 - 1 retiré) * 30 = 285
  assert.equal(t.sourceToTimelineFrame(10.5), 285);
});

test('silence < 0.25 s → coupe rejetée', () => {
  const block = { ...emptyBlock, jump_cuts: [{ cut_at_sec: 5, removes_sec: 0.1 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.segments.length, 1);
  assert.ok(t.dropped.some((d) => String(d.reason).includes('silence')));
});

test('cuts chevauchants → le second est rejeté', () => {
  // silence 1 : [2,5] ; le second cut (à 4 s) tombe DEDANS → rejeté
  const block = { ...emptyBlock, jump_cuts: [{ cut_at_sec: 5, removes_sec: 3 }, { cut_at_sec: 4, removes_sec: 2 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.segments.length, 2);
  assert.ok(t.dropped.some((d) => String(d.reason).includes('chevauche')));
});

/* ── Punch-ins ── */

test('punch-in : peak plafonné à 1.15, paramètres par défaut', () => {
  const block = { ...emptyBlock, punchins: [{ at_sec: 5, scale_to: 2.0 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.punchins[0].scale_to, 1.15);
  assert.equal(t.punchins[0].frame, 150);
});

test('courbe punch-in : montée, tenue, redescente vers 1', () => {
  const p = [{ frame: 100, scale_to: 1.08, attack_frames: 3, hold_frames: 6, release_frames: 9 }];
  const near = (a, b) => Math.abs(a - b) < 1e-9;
  assert.equal(caviarPunchScaleAtFrame(p, 50), 1);
  assert.ok(near(caviarPunchScaleAtFrame(p, 102), 1 + 0.08 * (2 / 3)));
  assert.ok(near(caviarPunchScaleAtFrame(p, 106), 1.08));
  const mid = caviarPunchScaleAtFrame(p, 112);
  assert.ok(mid > 1 && mid < 1.08, `redescente en cours : ${mid}`);
  assert.ok(near(caviarPunchScaleAtFrame(p, 118), 1));
});

/* ── B-roll numéroté + flash ENTRÉE + SFX ── */

test('pas de vidéo = pas de B-roll (fichier non résolu déposé)', () => {
  const block = { ...emptyBlock, brolls: [{ at_sec: 8, numero: 1 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.deepEqual(t.brolls, []);
  assert.deepEqual(t.flashes, []);
  assert.ok(t.dropped.some((d) => String(d.reason).includes('pas de vidéo')));
});

test('B-roll résolu → overlay + flash ENTRÉE seule (jamais à la sortie)', () => {
  const block = { ...emptyBlock, brolls: [{ at_sec: 8, numero: 1, file: 'broll/broll_01.mp4', sfx: 'impact' }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.brolls.length, 1);
  assert.equal(t.brolls[0].file, 'broll/broll_01.mp4');
  assert.deepEqual(t.flashes, [{ frame: 240, frames: 5 }]);
  // aucune trace de flash à la sortie (frame 240 + 45)
  assert.ok(!t.flashes.some((f) => f.frame === 285));
  // courbe : visible dès la 1re frame, retombe à 0 en fin de flash
  assert.ok(caviarFlashOpacityAtFrame(t.flashes, 240) > 0);
  assert.ok(caviarFlashOpacityAtFrame(t.flashes, 245) === 0);
});

test('B-roll plafonné à max_frames (45) et fx_mode=off dépose effets (garde jump cuts)', () => {
  const long = { ...emptyBlock, brolls: [{ at_sec: 8, file: 'a.mp4', duration_frames: 200 }] };
  const t1 = buildCaviarTimeline(long, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t1.brolls[0].frames, 45);

  const mixed = { ...emptyBlock, jump_cuts: [{ cut_at_sec: 10, removes_sec: 1 }], punchins: [{ at_sec: 5 }], brolls: [{ at_sec: 8, file: 'a.mp4' }] };
  const t2 = buildCaviarTimeline(mixed, budget, { fps: 30, speed: 1, durationInFrames: 900, fxOff: true });
  assert.equal(t2.segments.length, 2, 'jump cuts conservés en fx_mode=off');
  assert.deepEqual(t2.punchins, []);
  assert.deepEqual(t2.brolls, []);
  assert.ok(t2.dropped.some((d) => d.kind === 'brolls'));
  assert.ok(t2.dropped.some((d) => d.kind === 'punchins'));
});

/* ── Smash audio (ducking) ── */

test('ducking : −12 dB au climax, neutre ailleurs', () => {
  const smash = [{ frame: 300, duck_db: -12, duration_sec: 0.8 }];
  assert.equal(caviarDuckVolumeAtFrame(smash, 100), 1);
  const mid = caviarDuckVolumeAtFrame(smash, 315);
  assert.ok(Math.abs(mid - 0.2512) < 0.001, `10^(-12/20)=0.2512, obtenu ${mid}`);
  assert.equal(caviarDuckVolumeAtFrame(smash, 330), 1);
});

test('smash exporté vers la timeline au bon frame source→timeline', () => {
  const block = { ...emptyBlock, jump_cuts: [{ cut_at_sec: 10, removes_sec: 1 }], smash_audio: [{ at_sec: 12, duck_db: -9 }] };
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.smash_audio[0].frame, 330);
  assert.equal(t.smash_audio[0].duck_db, -9);
});

/* ── Normalisation ── */

test('normalizeCaviarBlock : entrées pourries → valeurs sûres', () => {
  const n = normalizeCaviarBlock({ enabled: 'yes', jump_cuts: 'x', punchins: null, brolls: [{}], smash_audio: 42 });
  assert.equal(n.enabled, false);
  assert.deepEqual(n.jump_cuts, []);
  assert.deepEqual(n.punchins, []);
  assert.deepEqual(n.brolls, [{}]);
  assert.deepEqual(n.smash_audio, []);
});

/* ── Syntaxe JSX du wiring composition (parité preview/CI) ── */

test('passthrough caviar : parsePurPack conserve le bloc du pack (parité preview/CI)', async () => {
  // Le passthrough vit dans bridgeClipper.js (F03_PREVIEW + miroir F03_PICTOR).
  // On vérifie ici les DEUX miroirs : identiques bit à bit + passthrough présent.
  const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
  const preview = read('../../../F03_PREVIEW/CODEBASE/src/preview/bridgeClipper.js');
  const pictor = read('../src/bridgeClipper.js');
  assert.equal(preview, pictor, 'miroirs bridgeClipper divergents — parité rompue');
  assert.ok(preview.includes("caviar: (pack.caviar"), 'passthrough parsePurPack absent');
  assert.ok(preview.includes('caviar: base.caviar'), 'passthrough parsePurPackMulti absent');
  assert.ok(preview.includes('entry.caviar = (pack.caviar'), 'passthrough par entrée absent');
});

test('purPackComposition.jsx : syntaxe valide (transform esbuild si présent)', async () => {
  let esbuild = null;
  try { esbuild = (await import('esbuild')).default; } catch { /* CI : npm ci le fournit */ }
  if (!esbuild) { console.log('  ↷ esbuild absent — test sauté (npm ci le fournira)'); return; }
  esbuild.transformSync(readFileSync(new URL('../src/purPackComposition.jsx', import.meta.url), 'utf8'), { loader: 'jsx' });
});

/* Runner minimal (aucune dépendance externe). */
runSuite();
