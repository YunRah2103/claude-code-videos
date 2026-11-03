// Render an episode's Three.js scene to 270x480 PNG frames with the pre-installed Chromium (Playwright).
//   node shared/assets/pix3d/render3d.mjs <scene.js> <out_dir> <fps> <t0> <t1> [step]
//   node shared/assets/pix3d/render3d.mjs <scene.js> <out_dir> <fps> --times 0,1.3,4.5   (preview stills)
// Writes <out_dir>/f_<frame>.png and <out_dir>/anchors.json ({frame: {name: [x, y, scale]}} in 1080x1920 px).
// Frame numbers are absolute (round(t * fps)), so partial renders merge into the same folder.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');   // global install (NODE_PATH)
import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';
const [scene, out, fps, t0, t1, step = '1'] = process.argv.slice(2);
const here = path.dirname(url.fileURLToPath(import.meta.url));
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 270, height: 480 } });
page.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
page.on('pageerror', e => { console.error('pageerror:', e.message); process.exit(1); });
await page.goto(url.pathToFileURL(path.join(here, 'page.html')).href + '?scene=' + encodeURIComponent(url.pathToFileURL(path.resolve(scene)).href));
await page.waitForFunction('window.READY === true', null, { timeout: 60000 });
const apath = path.join(out, 'anchors.json');
const anchors = fs.existsSync(apath) ? JSON.parse(fs.readFileSync(apath)) : {};
const F0 = Math.round(+t0 * +fps), F1 = Math.round(+t1 * +fps);
const list = t0 === '--times' ? t1.split(',').map(x => Math.round(+x * +fps)) : null;
const frames = list || Array.from({ length: Math.ceil((F1 - F0) / +step) }, (_, i) => F0 + i * +step);
for (const n of frames) {
  const r = await page.evaluate(t => window.renderAt(t), n / +fps);
  fs.writeFileSync(path.join(out, `f_${n}.png`), Buffer.from(r.png.split(',')[1], 'base64'));
  anchors[n] = r.anchors;
  if (!list && (n - F0) % 300 === 0) console.log(`3d ${n - F0}/${F1 - F0}`);
}
fs.writeFileSync(apath, JSON.stringify(anchors));
await browser.close();
