// Dusk city street (metres): road along X, sidewalks, two rows of flat-shaded buildings with emissive windows,
// lamp posts with glow sprites, lane markings, a striped barrier. Far geometry goes on layer 1 (rendered
// separately and blurred for depth of field). No text, logos or plates anywhere.
import * as THREE from 'three';
export const rng = s => () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
const cv = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; };
export function glowTex() { return cv(128, 128, (g, w) => { const r = g.createRadialGradient(64, 64, 0, 64, 64, 64); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.25, 'rgba(255,255,255,.45)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, w, w); }); }
function windowTex(seed) { const r = rng(seed); return cv(128, 256, (g, w, h) => {
  g.fillStyle = '#000'; g.fillRect(0, 0, w, h);
  for (let y = 8; y < h - 8; y += 16) for (let x = 6; x < w - 6; x += 14) { const v = r(); if (v < .42) { g.fillStyle = v < .3 ? '#ffc477' : v < .38 ? '#ffe6b0' : '#8fe3ff'; g.fillRect(x, y, 8, 10); } }
}); }
export function stripeTex() { return cv(128, 32, (g, w, h) => { g.fillStyle = '#ffd23f'; g.fillRect(0, 0, w, h); g.fillStyle = '#15151c'; for (let x = -32; x < w; x += 32) { g.beginPath(); g.moveTo(x, h); g.lineTo(x + 16, 0); g.lineTo(x + 32, 0); g.lineTo(x + 16, h); g.fill(); } }); }
export function buildStreet(scene, o = {}) {
  const near = new THREE.Group(), far = new THREE.Group(); scene.add(near, far);
  const x0 = o.x0 ?? -70, x1 = o.x1 ?? 50;
  scene.background = cv(4, 512, (g, w, h) => { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#1b1c4a'); gr.addColorStop(.45, '#5b3b7a'); gr.addColorStop(.7, '#d06a7c'); gr.addColorStop(.85, '#ffb26b'); gr.addColorStop(1, '#ffcf8a'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
  scene.fog = new THREE.Fog('#8a5f8e', 18, 85);
  scene.add(new THREE.HemisphereLight('#b3a6ff', '#3a2a40', 1.8));
  const key = new THREE.DirectionalLight('#ffb27a', 2.0); key.position.set(-14, 9, 12); scene.add(key);
  const rim = new THREE.DirectionalLight('#6fd3ff', 1.1); rim.position.set(10, 7, -12); scene.add(rim);
  const lam = c => new THREE.MeshLambertMaterial({ color: c, flatShading: true });
  // road, markings, sidewalks
  const road = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0 + 200, 12), lam('#34324f')); road.rotation.x = -Math.PI / 2; road.position.set((x0 + x1) / 2, 0, 0); near.add(road);
  const dash = new THREE.BoxGeometry(2.2, .01, .14), wm = new THREE.MeshBasicMaterial({ color: '#d9d4c8' });
  for (let x = x0 - 60; x < x1 + 60; x += 5) { const d = new THREE.Mesh(dash, wm); d.position.set(x, .006, 0); near.add(d); }
  for (const s of [-1, 1]) { const sw = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0 + 200, .16, 4), lam('#3c3a5c')); sw.position.set((x0 + x1) / 2, .08, s * 8); near.add(sw);
    const curb = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0 + 200, .17, .25), lam('#57557a')); curb.position.set((x0 + x1) / 2, .085, s * 6.1); near.add(curb); }
  // buildings (two rows each side)
  const r = rng(11), body = ['#4a3f78', '#56467f', '#3f3a6c', '#5d4a7e'], texs = [1, 2, 3, 4].map(windowTex);
  for (const side of [-1, 1]) for (const row of [0, 1]) {
    let x = x0 - 40; while (x < x1 + 40) { const w = 5 + r() * 9, d = 6 + r() * 6, h = row ? 12 + r() * 26 : 3.5 + r() * 6;
      const tex = texs[Math.floor(r() * 4)].clone(); tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(w / 3, h / 5.5); tex.needsUpdate = true;
      const m = new THREE.MeshLambertMaterial({ color: body[Math.floor(r() * 4)], emissive: '#ffffff', emissiveMap: tex, emissiveIntensity: .75, flatShading: true });
      const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); b.position.set(x + w / 2, h / 2, side * (10.5 + row * 32 + d / 2 + r() * (row ? 20 : 2))); far.add(b);
      if (r() < .4) { const top = new THREE.Mesh(new THREE.BoxGeometry(w * .5, 2 + r() * 3, d * .5), lam('#1a1a38')); top.position.set(x + w / 2, h + 1.5, b.position.z); far.add(top); }
      x += w + .4 + r() * 1.5; } }
  // lamp posts
  const glow = glowTex(), pole = lam('#2a2b45');
  const lamps = [];
  for (let x = x0; x < x1; x += 14) for (const s of [-1]) {
    const g = new THREE.Group(); g.position.set(x, 0, s * 6.6);
    const p = new THREE.Mesh(new THREE.CylinderGeometry(.08, .11, 6.2, 8), pole); p.position.y = 3.1; g.add(p);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(.08, .08, 1.4), pole); arm.position.set(0, 6.1, -s * .65); g.add(arm);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(.16, 10, 8), new THREE.MeshBasicMaterial({ color: '#fff0c8' })); bulb.position.set(0, 5.98, -s * 1.25); g.add(bulb);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow, color: '#ffb866', transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: .8 })); sp.scale.set(3, 3, 1); sp.position.copy(bulb.position); g.add(sp);
    near.add(g); lamps.push(g); }
  far.traverse(o => o.layers.set(1));
  return { near, far, lamps };
}
export function barrier(x, z = 0) {
  const g = new THREE.Group(), st = stripeTex(); st.wrapS = THREE.RepeatWrapping; st.repeat.set(3, 1);
  const m = new THREE.MeshLambertMaterial({ color: '#d8d2c8', flatShading: true });
  const base = new THREE.Mesh(new THREE.BoxGeometry(.7, .35, 4.4), m); base.position.y = .18; g.add(base);
  const top = new THREE.Mesh(new THREE.BoxGeometry(.35, .5, 4.4), m); top.position.y = .6; g.add(top);
  const band = new THREE.Mesh(new THREE.BoxGeometry(.37, .22, 4.42), new THREE.MeshLambertMaterial({ map: st })); band.position.y = .66; g.add(band);
  g.position.set(x, 0, z); return g;
}
