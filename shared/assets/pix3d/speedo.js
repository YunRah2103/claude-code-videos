// The speedometer wall: a big low-poly dial on a steel panel (segments light up to a value, red limit line,
// needle, glowing pixel digits for the limit) plus the "invisible" force-field wall the cars hit.
// No scale numbers other than the limit, so an episode never shows a speed it doesn't state.
import * as THREE from 'three';
import { P } from './palette.js';
import { mat, voxelDigits, pixTex, hex } from './voxel.js';

const A0 = 225, SWEEP = 270;                          // degrees: 0 at A0, max at A0 - SWEEP (clockwise)
export const angleOf = (v, vmax) => THREE.MathUtils.degToRad(A0 - SWEEP * v / vmax);

export function speedo({ r = 30, vmax = 200, limit = 155, segs = 40 } = {}) {
  const g = new THREE.Group();
  const panel = new THREE.Mesh(new THREE.BoxGeometry(r * 2.6, r * 2.5, 3), mat(P.silverSh)); panel.position.z = -1.6; g.add(panel);
  for (const [x, y] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const b = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 1), mat(P.silverHi)); b.position.set(x * r * 1.18, y * r * 1.12, 0.2); g.add(b);
  }
  const bezel = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.08, r * 1.08, 2.4, 20), mat(P.silverHi)); bezel.rotation.x = Math.PI / 2; g.add(bezel);
  const face = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 2.6, 20), mat(0x101116)); face.rotation.x = Math.PI / 2; g.add(face);
  const offM = mat(0x2a2c34), segMeshes = [];
  for (let i = 0; i < segs; i++) {
    const v = (i + 0.5) / segs * vmax, a = angleOf(v, vmax);
    const m = new THREE.Mesh(new THREE.BoxGeometry(r * 0.16, r * 2 * Math.PI * 0.75 / segs * 0.7, 1), offM);
    m.position.set(Math.cos(a) * r * 0.84, Math.sin(a) * r * 0.84, 1.6); m.rotation.z = a; g.add(m); segMeshes.push({ m, v });
  }
  for (let i = 0; i <= 10; i++) {                       // plain tick marks (no numbers)
    const a = angleOf(i / 10 * vmax, vmax), m = new THREE.Mesh(new THREE.BoxGeometry(r * 0.1, 0.7, 1), mat(P.silverHi));
    m.position.set(Math.cos(a) * r * 0.66, Math.sin(a) * r * 0.66, 1.6); m.rotation.z = a; g.add(m);
  }
  const la = angleOf(limit, vmax);
  const limitLine = new THREE.Mesh(new THREE.BoxGeometry(r * 0.5, 1.4, 1.4), mat(P.red, true));
  limitLine.position.set(Math.cos(la) * r * 0.86, Math.sin(la) * r * 0.86, 2.0); limitLine.rotation.z = la; g.add(limitLine);
  const needle = new THREE.Group(); const nm = new THREE.Mesh(new THREE.BoxGeometry(r * 0.78, 1.2, 0.8), mat(P.red, true));
  nm.position.x = r * 0.36; needle.add(nm); needle.position.z = 2.4; g.add(needle);
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 1.5, 8), mat(P.silverHi)); cap.rotation.x = Math.PI / 2; cap.position.z = 2.8; g.add(cap);
  const digits = voxelDigits(String(limit), P.glow, { size: r * 0.075, depth: 1 }); digits.position.set(0, -r * 0.66, 2); g.add(digits);
  const glowMat = new THREE.MeshBasicMaterial({ color: P.glow, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
  const halo = new THREE.Mesh(new THREE.PlaneGeometry(r * 0.95, r * 0.5), glowMat); halo.position.set(0, -r * 0.66 + r * 0.19, 1.8); g.add(halo);
  const onM = mat(P.glow, true), hotM = mat(P.red, true);
  const api = {
    group: g, needle, digits, limitLine,
    // value: needle position; fill: lit segments up to this value; glow 0..1: digit halo; limitOn: red line visible
    set({ value = 0, fill = 0, glow = 0, limitOn = true, t = 0 }) {
      needle.rotation.z = angleOf(value, vmax);
      segMeshes.forEach(({ m, v }) => { m.material = v <= fill ? (v > limit - 18 ? hotM : onM) : offM; });
      glowMat.opacity = 0.18 + 0.5 * glow * (0.8 + 0.2 * Math.sin(t * 20));
      digits.scale.setScalar(1 + 0.12 * glow * Math.max(0, Math.sin(t * 9)));
      limitLine.visible = limitOn;
    },
  };
  api.set({});
  return api;
}

// Force-field wall: faint hex-grid plane that flashes and ripples when hit; can shatter into voxel shards.
export function forceWall({ w = 70, h = 30 } = {}) {
  const g = new THREE.Group();
  const tex = pixTex(16, 16, c => { c.fillStyle = '#000'; c.fillRect(0, 0, 16, 16); c.fillStyle = hex(P.glow);
    c.fillRect(0, 0, 16, 1); c.fillRect(0, 0, 1, 16); c.fillRect(8, 8, 1, 1); }, [w / 8, h / 8]);
  const m = new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(w, h, 12, 6), m); plane.position.y = h / 2; g.add(plane);
  const base = plane.geometry.attributes.position.array.slice();
  const posts = [];
  for (const s of [-1, 1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(2.5, h + 2, 2.5), mat(P.silverSh)); p.position.set(s * (w / 2 + 1.25), (h + 2) / 2, 0); g.add(p); posts.push(p);
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(2.7, 2, 2.7), mat(P.glow, true)); lamp.position.set(s * (w / 2 + 1.25), h + 2, 0); g.add(lamp); posts.push(lamp); }
  // shards for the unlock: small voxel cubes laid out on the wall
  const shards = [];
  for (let i = 0; i < 48; i++) {
    const s = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 0.6), mat(i % 3 ? P.glow : P.glowHi, true));
    s.userData = { x: ((i % 12) + 0.5) / 12 * w - w / 2, y: (Math.floor(i / 12) + 0.5) / 4 * h, vx: ((i * 37) % 11 - 5) * 6, vy: 10 + (i * 13) % 17 * 2, vz: 12 + (i * 7) % 9 * 4, spin: (i % 5) - 2 };
    s.visible = false; g.add(s); shards.push(s);
  }
  return {
    group: g, plane, posts,
    // hit: seconds since last impact (or <0 for none), at: impact x; opacity base; shatter: seconds since the unlock (<0 none)
    set({ hit = -1, at = 0, base: b = 0.1, shatter = -1, t = 0 }) {
      const k = hit >= 0 ? Math.exp(-hit * 4) : 0;
      m.opacity = shatter >= 0 ? 0 : Math.min(1, b + 0.75 * k + 0.03 * Math.sin(t * 12));
      const pos = plane.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const x = base[i * 3], y = base[i * 3 + 1], d = Math.hypot(x - at, y + h / 2 - 8);
        pos.array[i * 3 + 2] = hit >= 0 ? -3 * k * Math.sin(d * 0.35 - hit * 30) : 0;
      }
      pos.needsUpdate = true;
      shards.forEach(s => { const u = s.userData; s.visible = shatter >= 0 && shatter < 1.6;
        if (s.visible) { const tt = shatter; s.position.set(u.x + u.vx * tt, Math.max(1, u.y + u.vy * tt - 40 * tt * tt), u.vz * tt); s.rotation.set(tt * u.spin * 4, tt * u.spin * 3, 0); } });
    },
  };
}
