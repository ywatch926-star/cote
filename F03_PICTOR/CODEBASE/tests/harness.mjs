/* Mini runner de tests — zéro dépendance externe (CI-friendly).
   Usage : import { test, ok, eq, runSuite } from './harness.mjs'; */
const tests = [];

export function test(name, fn) {
  tests.push([name, fn]);
}

export function ok(cond, msg = 'condition attendue vraie') {
  if (!cond) throw new Error(msg);
}

export function eq(a, b, msg = 'égalité attendue') {
  if (a !== b) throw new Error(`${msg} : ${JSON.stringify(a)} !== ${JSON.stringify(b)}`);
}

export async function runSuite() {
  let failed = 0;
  for (const [name, fn] of tests) {
    try {
      await fn();
      console.log(`  ✓ ${name}`);
    } catch (err) {
      failed += 1;
      console.error(`  ✗ ${name}\n    ${err && err.message ? err.message : err}`);
    }
  }
  console.log(`\n${tests.length - failed}/${tests.length} tests OK`);
  if (failed > 0) process.exit(1);
}
