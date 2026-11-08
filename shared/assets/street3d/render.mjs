// Deterministic Three.js frame renderer (Chromium + Playwright, SwiftShader WebGL), 1080x1920, parallel pages.
//   node shared/assets/street3d/render.mjs <scene.js> <data.json> <out_dir> <fps> <t0> <t1> [workers] [--times a,b]
// Writes f_%05d.png (index from round(t0*fps); with --times, absolute frame index), boxes.json, events.json.
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path'; import url from 'url';
const { chromium } = createRequire(import.meta.url)('playwright');
const here = path.dirname(url.fileURLToPath(import.meta.url));
const [scene, dataPath, out, fpsS, t0S, t1S, wS] = process.argv.slice(2);
const fps = +fpsS, t0 = +t0S, t1 = +t1S, workers = +(wS || 3), ti = process.argv.indexOf('--times');
const frames = ti > 0 ? process.argv[ti + 1].split(',').map(t => Math.round(+t * fps)) : [...Array(Math.round((t1 - t0) * fps)).keys()].map(i => i + Math.round(t0 * fps));
const base = ti > 0 ? 0 : Math.round(t0 * fps);
fs.mkdirSync(out, { recursive: true });
const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files', '--ignore-gpu-blocklist'] });
const boxes = {}; let events = null, done = 0;
async function work(list) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => { console.error('pageerror:', e.message); process.exit(1); });
  page.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
  await page.goto(url.pathToFileURL(path.join(here, 'page.html')).href + '?scene=' + encodeURIComponent(url.pathToFileURL(path.resolve(scene)).href));
  await page.waitForFunction('window.READY === true');
  events = await page.evaluate(d => window.BUILD(d), data);
  for (const f of list) {
    const r = await page.evaluate(([f, fps]) => window.renderAt(f, fps), [f, fps]);
    fs.writeFileSync(path.join(out, `f_${String(f - base).padStart(5, '0')}.png`), Buffer.from(r.u.split(',')[1], 'base64'));
    boxes[f] = r.b; if (++done % 120 === 0) console.log('frames', done);
  }
  await page.close();
}
await Promise.all([...Array(workers)].map((_, k) => work(frames.filter((_, i) => i % workers === k))));
await browser.close();
fs.writeFileSync(path.join(out, 'boxes.json'), JSON.stringify(boxes));
if (events) fs.writeFileSync(path.join(out, 'events.json'), JSON.stringify(events, null, 1));
console.log('frames', frames.length);
