// Runs the page's own JavaScript (src/math-core.js verbatim from the original, src/field.js lifted from it)
// under Node and prints what the Python witnesses compare against: settled sources, heights on a grid,
// and the page's geodesic traces at the original's step and at half and quarter that step.
//   node tools/parity.mjs <time> [grid=161]      (one JSON object on stdout)
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
for (const f of ['src/math-core.js', 'src/field.js']) vm.runInThisContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), { filename: f });
const { ManifoldMath, ManifoldField } = globalThis;

const time = Number(process.argv[2] ?? 3.7), N = Number(process.argv[3] ?? 161), E = 11.2;
const out = { time, grid: N, extent: E, moods: [] };
for (let mood = 0; mood < 4; mood++) {
  const F = ManifoldField.create(mood);
  F.time = time; F.settle();
  const heights = new Array(N * N);
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const x = (i / (N - 1) * 2 - 1) * E, z = (j / (N - 1) * 2 - 1) * E;
    heights[j * N + i] = F.heightAt(x, z);
  }
  // The page's trace bundle at the original's 'balanced' level: 22 traces from x = -10.5.
  const prepared = ManifoldMath.prepare(F.sources), traces = [];
  const n = 22;
  for (let i = 0; i < n; i++) {
    const z = -8.2 + 16.4 * i / (n - 1), theta = .08 * Math.sin(i * .7 + time * .07);
    const runs = {};
    for (const [k, step, count] of [['h', .13, 200], ['h2', .065, 400], ['h4', .0325, 800]])
      runs[k] = ManifoldMath.trace(-10.5, z, theta, prepared, { step, count, bound: 10.7 });
    traces.push({ z, theta, ...runs });
  }
  // A single isotropic source for the Clairaut reference.
  const iso = [{ x: 0, z: 0, amp: 4.5, sx: 1.6, sz: 1.6, angle: 0 }];
  const isoTraces = [];
  for (const b of [0.6, 1.4, 2.6]) {
    const runs = {};
    for (const [k, step, count] of [['h', .13, 160], ['h2', .065, 320], ['h4', .0325, 640]])
      runs[k] = ManifoldMath.trace(-10, b, 0, ManifoldMath.prepare(iso), { step, count, bound: 11 });
    isoTraces.push({ b, ...runs });
  }
  const K = [];
  for (const [x, z] of [[0, 0], [1.3, -2.2], [-4.1, 3.3], [6.2, 5.5], [-7.7, -8.1]]) K.push({ x, z, ...ManifoldMath.sample(x, z, F.sources) });
  out.moods.push({ mood, name: F.presets[mood].name, sources: F.sources, heights, traces, iso, isoTraces, K });
}
process.stdout.write(JSON.stringify(out));
