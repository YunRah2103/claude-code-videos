// Deterministic frame renderer for inkfight scenes (Chromium canvas via Playwright).
//   node shared/assets/inkfight/render.mjs <scene.js> <data.json> <out_dir> <fps> <t0> <t1> [workers] [--times a,b,c]
// Loads kit.js + the scene (classic scripts). The scene defines window.SCENE = { init(data), frame(i, fps) }.
// Writes out_dir/f_%05d.png (frame index from 0 at t0) and out_dir/boxes.json (text boxes per frame) + events.json.
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const require = createRequire(import.meta.url); const { chromium } = require('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const [scene, dataPath, out, fpsS, t0S, t1S, wS] = process.argv.slice(2);
const fps = +fpsS, t0 = +t0S, t1 = +t1S, workers = +(wS || 4);
const ti = process.argv.indexOf('--times');
const frames = ti > 0 ? process.argv[ti + 1].split(',').map(t => Math.round(+t * fps)) : [...Array(Math.round((t1 - t0) * fps)).keys()].map(i => i + Math.round(t0 * fps));
fs.mkdirSync(out, { recursive: true });
const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const browser = await chromium.launch();
const boxes = {}; let events = null;
async function work(list) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.setContent('<html><body style="margin:0;background:#000"><canvas id="c" width="1080" height="1920"></canvas></body></html>');
  await page.addScriptTag({ path: path.join(here, 'kit.js') }); await page.addScriptTag({ path: scene });
  await page.evaluate(async d => { await document.fonts.load('900 64px "Inter Display"'); await document.fonts.load('800 64px Inter'); window.SCENE.init(d); }, data);
  events = await page.evaluate(() => window.SCENE.events || null);
  for (const f of list) {
    const r = await page.evaluate(([f, fps]) => { K.boxes = []; window.SCENE.frame(f, fps); return { u: document.getElementById('c').toDataURL('image/png'), b: K.boxes }; }, [f, fps]);
    fs.writeFileSync(path.join(out, `f_${String(f - (ti > 0 ? 0 : Math.round(t0 * fps))).padStart(5, '0')}.png`), Buffer.from(r.u.split(',')[1], 'base64'));
    boxes[f] = r.b;
  }
  await page.close();
}
const parts = [...Array(workers)].map((_, k) => frames.filter((_, i) => i % workers === k));
await Promise.all(parts.map(work));
await browser.close();
fs.writeFileSync(path.join(out, 'boxes.json'), JSON.stringify(boxes));
if (events) fs.writeFileSync(path.join(out, 'events.json'), JSON.stringify(events, null, 1));
console.log('frames', frames.length);
