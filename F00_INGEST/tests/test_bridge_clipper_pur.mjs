// Test BridgeClipper v2 — packs PUR réels A01/A02/A03 (fixtures extraites de PERTURABO EXPORT)
// Run: node F00_INGEST/tests/test_bridge_clipper_pur.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parsePurPack, extractOverlayLines, normalizePurAntiDetection, normalizePurZooms } from '../../F03_PREVIEW/CODEBASE/src/preview/bridgeClipper.js';

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = ['pur_A01.json', 'pur_A02.json', 'pur_A03.json'].map((f) =>
  JSON.parse(readFileSync(join(here, 'fixtures', f), 'utf-8')));

let failures = 0;
const check = (cond, label) => {
  if (cond) console.log(`  [✓] ${label}`);
  else { failures += 1; console.error(`  [✗] ${label}`); }
};

console.log('── Test 1 : extractOverlayLines (copywriting v2) ──');
for (const [i, pack] of fixtures.entries()) {
  const lines = extractOverlayLines(pack.copywriting || {});
  check(lines.length >= 1 && lines.length <= 2, `A0${i + 1} : ${lines.length} ligne(s) extraite(s) : « ${lines[0] || '—'} »`);
}

console.log('── Test 2 : parsePurPack sur les 3 packs réels ──');
for (const [i, pack] of fixtures.entries()) {
  const m = parsePurPack(pack, { fps: 30, clipFiles: [`clips/pur_A0${i + 1}.mp4`] });
  check(m.schema_version === 'dev10.pur.v1', `A0${i + 1} schema_version = dev10.pur.v1`);
  check(m.mode === 'pur_pack', `A0${i + 1} mode = pur_pack`);
  check(m.entries.length === 1, `A0${i + 1} 1 entrée`);
  check(m.entries[0].clip_file === `clips/pur_A0${i + 1}.mp4`, `A0${i + 1} clip_file câblé`);
  check(Math.abs(m.entries[0].duration_seconds - pack.source.duration_sec) < 0.01, `A0${i + 1} durée = ${m.entries[0].duration_seconds}s (pack: ${pack.source.duration_sec}s)`);
  check(m.narrative.overlay.lines.length >= 1, `A0${i + 1} overlay non vide (${m.narrative.overlay.lines.length} ligne(s))`);
  check(m.pur.source === pack.montage_instructions.segment.source_url, `A0${i + 1} vod_url propagée`);
  check(m.entries[0].zooms.length >= 1, `A0${i + 1} zooms parseés : ${m.entries[0].zooms.length}`);
  check(m.entries[0].anti_detection.mirror === true, `A0${i + 1} mirror=true (obligatoire PUR)`);
  check(m.entries[0].anti_detection.speed >= 1.0 && m.entries[0].anti_detection.speed <= 1.1, `A0${i + 1} speed = ${m.entries[0].anti_detection.speed}`);
  check(m.total_frames > 0, `A0${i + 1} total_frames = ${m.total_frames}`);
}

console.log('── Test 3 : valeurs anti-détection (doctrine PUR) ──');
const adA01 = normalizePurAntiDetection(fixtures[0].montage_instructions);
check(adA01.speed === 1.05, `speed optimal 1.05 lu depuis "optimal": ${adA01.speed}`);
check(adA01.crop_pct === 2.5, `crop 2.5% lu : ${adA01.crop_pct}`);
const zoomsA01 = normalizePurZooms(fixtures[0].montage_instructions.body.zooms, [], 30);
const firstZoom = zoomsA01[0];
check(firstZoom.scale_from > 1 && firstZoom.scale_to >= firstZoom.scale_from, `zoom A01 : ${firstZoom.scale_from}→${firstZoom.scale_to} @ frame ${firstZoom.moment_frame}`);

console.log('── Test 4 : canvas adaptatif ──');
const m169 = parsePurPack(fixtures[0], { canvas: '16:9' });
check(m169.canvas.width === 1920 && m169.canvas.height === 1080, 'canvas 16:9 → 1920x1080');
const m11 = parsePurPack(fixtures[0], { canvas: '1:1' });
check(m11.canvas.width === 1080 && m11.canvas.height === 1080, 'canvas 1:1 → 1080x1080');

console.log('── Test 5 : dégénéré ──');
const empty = parsePurPack(null);
check(empty.entries.length === 0 && empty.total_frames === 0, 'pack null → manifeste vide propre');

if (failures > 0) { console.error(`\n✗ ${failures} échec(s)`); process.exit(1); }
console.log('\n✓ Tous les tests BridgeClipper PUR passent.');
