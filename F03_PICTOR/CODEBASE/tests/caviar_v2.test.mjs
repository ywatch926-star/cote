/* ═══════════════════════════════════════════════════════════════════
   Tests Groupe 1 v2 — adaptateur pack v2 (partition F00D) → moteur
   Exécution : node tests/caviar_v2.test.mjs (inclus dans npm run test:caviar)
   Fixture : le pack RÉEL voxc-2 (récupéré en lecture seule depuis la branche
   v2-live-vox-c de PERTURABO) — la vérité terrain, pas un schéma inventé.
   ═══════════════════════════════════════════════════════════════════ */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test, runSuite } from './harness.mjs';

import {
  detectPackSchema,
  resolveSemanticBroll,
  normalizeCaviarPartition,
  packToCaviarBlock,
  toEngineBlock,
} from '../src/caviarV2.js';
import {
  buildCaviarTimeline,
  verifyCaviarBudget,
} from '../src/caviarRender.js';

const budget = JSON.parse(readFileSync(new URL('../src/data/caviar_budget.json', import.meta.url), 'utf8'));
const registry = JSON.parse(readFileSync(new URL('../src/data/caviar_registry.json', import.meta.url), 'utf8'));

// Fixture : le pack réel (vérité terrain). Si absent (sandbox hors ligne),
// les tests sur le pack réel sont sautés — les tests synthétiques restent.
let realPack = null;
try { realPack = JSON.parse(readFileSync(new URL('./pack_voxc2_blur_v2.json', import.meta.url), 'utf8')); } catch { /* skip */ }

/* ── Détection de schéma ── */

test('détection : v2 / v1 / v0 — jamais d\'échec sur vieilles clés absentes', () => {
  assert.equal(detectPackSchema({ caviar_partition: { bound: true } }), 'v2');
  assert.equal(detectPackSchema({ caviar: { enabled: true } }), 'v1');
  assert.equal(detectPackSchema({}), 'v0');
  // Piège note §5 : un pack v2 n'a PAS angle/cut_directives/text_payload…
  assert.equal(detectPackSchema({ asset_mode: 'blur', montage_instructions: {}, caviar_partition: {} }), 'v2');
  assert.equal(detectPackSchema(null), 'v0');
});

/* ── Registre sémantique + compat numéroté ── */

test('registre : BLUR-01 → fichier (sémantique v2)', () => {
  const r = resolveSemanticBroll('BLUR-01', registry);
  assert.ok(r && r.file === 'broll/BLUR-01.mp4');
  assert.equal(r.sfx, 'impact');
});

test('registre : id numérique → compat registre numéroté v1', () => {
  const v1registry = { clips: { 1: { file: 'broll/broll_01.mp4', sfx: 'impact' } } };
  const r = resolveSemanticBroll('1', v1registry);
  assert.ok(r && r.file === 'broll/broll_01.mp4');
});

test('registre : id inconnu → null (pas de vidéo = pas de B-roll)', () => {
  assert.equal(resolveSemanticBroll('NOPE-99', registry), null);
  assert.equal(resolveSemanticBroll('BLUR-01', null), null);
});

/* ── Mapping partition → moteur ── */

test('mapping : panels → brolls (start_sec→at_sec, fichier résolu, extra conservé)', () => {
  const block = normalizeCaviarPartition({
    bound: true,
    panels: [{ broll_id: 'BLUR-01', start_sec: 12.825, duration_frames: 36, crop_zoom: 1.3, blur_radius_px: 18, panel: 'vertical_text_overlay', entry_flash: true, sfx: 'impact', emotion_requested: 'incredulity' }],
  }, registry);
  assert.equal(block.enabled, true);
  assert.equal(block.brolls.length, 1);
  const b = block.brolls[0];
  assert.equal(b.at_sec, 12.825);
  assert.equal(b.file, 'broll/BLUR-01.mp4');
  assert.equal(b.extra.crop_zoom, 1.3);
  assert.equal(b.extra.blur_radius_px, 18);
  assert.equal(b.extra.panel, 'vertical_text_overlay');
  assert.equal(b.extra.emotion_requested, 'incredulity');
});

test('mapping : silence_trims → jump_cuts, events.punch_ins/smash_audio', () => {
  const block = normalizeCaviarPartition({
    silence_trims: [{ start_sec: 10, duration_sec: 0.6 }, { cut_at_sec: 20, removes_sec: 0.4 }],
    events: {
      punch_ins: [{ at_sec: 5, crop_zoom: 1.1 }],
      smash_audio: [{ at_sec: 28.216, duck_db: -12, duration_sec: 0.8 }],
      broll: [{ broll_id: 'BLUR-01', start_sec: 8, duration_frames: 30 }],
    },
  }, registry);
  assert.deepEqual(block.jump_cuts, [{ cut_at_sec: 10, removes_sec: 0.6 }, { cut_at_sec: 20, removes_sec: 0.4 }]);
  assert.equal(block.punchins[0].at_sec, 5);
  assert.equal(block.punchins[0].scale_to, 1.1);
  assert.equal(block.smash_audio[0].at_sec, 28.216);
  assert.equal(block.brolls[0].at_sec, 8);
});

test('mapping : partition vide/pourrie → bloc vide mais non null (null → null)', () => {
  for (const raw of [{}, { bound: false }, { panels: 'x', events: 42 }]) {
    const b = normalizeCaviarPartition(raw, registry);
    assert.ok(b, 'bloc retourné même pour entrée pourrie');
    assert.deepEqual(b.brolls, []);
    assert.deepEqual(b.jump_cuts, []);
  }
  assert.equal(normalizeCaviarPartition(null), null);
});

/* ── Intégration moteur : la partition v2 passe TOUT le pipeline v1 ── */

test('intégration : partition v2 → buildCaviarTimeline (flash entrée, budget, dépôt)', () => {
  const block = normalizeCaviarPartition({
    bound: true,
    panels: [
      { broll_id: 'BLUR-01', start_sec: 8, duration_frames: 36, entry_flash: true },
      { broll_id: 'NOPE-99', start_sec: 20, duration_frames: 36 }, // non résolu → déposé
    ],
    events: { smash_audio: [{ at_sec: 15, duck_db: -12, duration_sec: 0.8 }] },
  }, registry);
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.enabled, true);
  assert.equal(t.brolls.length, 1, 'seul le panneau résolu est rendu');
  assert.deepEqual(t.flashes, [{ frame: 240, frames: 5 }]);
  assert.ok(t.dropped.some((d) => String(d.reason).includes('pas de vidéo')));
  assert.equal(t.smash_audio[0].frame, 450);
});

test('intégration : budget vérifié sur le bloc v2 (dépassement → déposé)', () => {
  const block = normalizeCaviarPartition({
    bound: true,
    panels: [
      { broll_id: 'BLUR-01', start_sec: 3 }, { broll_id: 'BLUR-01', start_sec: 9 },
      { broll_id: 'BLUR-01', start_sec: 15 }, { broll_id: 'BLUR-01', start_sec: 22 },
    ],
  }, registry);
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1, durationInFrames: 900 });
  assert.equal(t.brolls.length, 3, 'cap broll 3 → le 4e est déposé');
  assert.ok(t.gate.ok);
});

/* ── Pack réel voxc-2 (vérité terrain) ── */

test('pack réel : détection v2 + budget_state cohérent avec notre recalcul', () => {
  if (!realPack) { console.log('  ↷ pack réel absent — sauté'); return; }
  assert.equal(detectPackSchema(realPack), 'v2');
  const block = packToCaviarBlock(realPack, registry);
  assert.equal(block.enabled, true);
  assert.equal(block.brolls.length, 2, 'BLUR-01 + BLUR-02');
  assert.equal(block.smash_audio.length, 1);
  const v = verifyCaviarBudget(block, budget);
  // Pack : 32u (2×12 + 1×8). Notre recalcul doit tomber pareil.
  assert.equal(v.spend_units, 32);
  assert.equal(v.ok, true);
  assert.ok(block.extra.budget_state?.caps_respected === true);
});

test('pack réel : toEngineBlock → timeline complète (flashs aux bons frames)', () => {
  if (!realPack) { console.log('  ↷ pack réel absent — sauté'); return; }
  const block = toEngineBlock(realPack.caviar_partition, registry);
  const t = buildCaviarTimeline(block, budget, { fps: 30, speed: 1.05, durationInFrames: Math.round((51.301 / 1.05) * 30) });
  assert.equal(t.enabled, true);
  // BLUR-01 @12.825s source → (12.825/1.05)*30 ≈ 366 frames timeline
  assert.equal(t.brolls[0].frame, Math.round((12.825 / 1.05) * 30));
  assert.equal(t.brolls[1].frame, Math.round((25.651 / 1.05) * 30));
  // flash = ENTRÉE de chaque B-roll
  assert.deepEqual(t.flashes.map((f) => f.frame), t.brolls.map((b) => b.frame));
  assert.equal(t.smash_audio[0].frame, Math.round((28.216 / 1.05) * 30));
  assert.equal(t.segments.length, 1, '0 jump cuts dans ce pack → 1 tuile continue');
});

/* ── Passthrough : les miroirs transportent caviar_partition ── */

test('passthrough v2 : miroirs bridgeClipper bit-à-bit + caviar_partition transporté', async () => {
  const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');
  const preview = read('../../../F03_PREVIEW/CODEBASE/src/preview/bridgeClipper.js');
  const pictor = read('../src/bridgeClipper.js');
  assert.equal(preview, pictor, 'miroirs bridgeClipper divergents');
  assert.ok(preview.includes('pack.caviar_partition'), 'passthrough v2 absent (racine)');
  assert.ok(preview.includes('entry.caviar = (pack.caviar'), 'passthrough v2 absent (entrée)');
  // Syntaxe valide :
  let esbuild = null;
  try { esbuild = (await import('esbuild')).default; } catch { /* CI : npm ci le fournit */ }
  if (esbuild) esbuild.transformSync(preview, { loader: 'jsx' });
});

runSuite();
