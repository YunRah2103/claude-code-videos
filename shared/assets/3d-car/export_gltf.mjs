// Export the procedural coupe to glTF (car + x-ray internals, standard materials):
//   node shared/assets/3d-car/export_gltf.mjs shared/assets/3d-car/coupe.gltf
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';
const here = path.dirname(url.fileURLToPath(import.meta.url));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
const page = await browser.newPage();
page.on('pageerror', e => { console.error('pageerror:', e.message); process.exit(1); });
await page.goto(url.pathToFileURL(path.join(here, '..', 'pix3d', 'page.html')).href + '?scene=' + encodeURIComponent(url.pathToFileURL(path.join(here, 'gltf_scene.js')).href));
await page.waitForFunction('window.READY === true', null, { timeout: 60000 });
fs.writeFileSync(process.argv[2], await page.evaluate(() => window.EP.gltf));
await browser.close();
