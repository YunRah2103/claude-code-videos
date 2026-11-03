// Voxel helpers: turn a pixel map (rows of chars) into merged flat-shaded boxes, and 3x5 pixel digits.
import * as THREE from 'three';

const box = new THREE.BoxGeometry(1, 1, 1);
const mats = new Map();
export function mat(col, emissive = false) {
  const k = col + (emissive ? 'e' : '');
  if (!mats.has(k)) mats.set(k, emissive ? new THREE.MeshBasicMaterial({ color: col })
                                         : new THREE.MeshLambertMaterial({ color: col, flatShading: true }));
  return mats.get(k);
}

// rows: array of strings, key: {char: color | [color, emissive]}; depth in voxels; size = voxel edge.
// Returns a Group centred on x, bottom at y=0, front face at z=depth*size/2. One InstancedMesh per colour.
export function voxelSprite(rows, key, { size = 1, depth = 1 } = {}) {
  const g = new THREE.Group(); const h = rows.length, w = Math.max(...rows.map(r => r.length));
  const per = {};
  rows.forEach((r, y) => [...r].forEach((c, x) => { if (key[c] !== undefined) (per[c] ||= []).push([x, h - 1 - y]); }));
  const m4 = new THREE.Matrix4();
  for (const [c, cells] of Object.entries(per)) {
    const [col, em] = Array.isArray(key[c]) ? key[c] : [key[c], false];
    const im = new THREE.InstancedMesh(box, mat(col, em), cells.length * depth); let i = 0;
    for (const [x, y] of cells) for (let z = 0; z < depth; z++) {
      m4.makeScale(size, size, size).setPosition((x - (w - 1) / 2) * size, (y + 0.5) * size, (z - (depth - 1) / 2) * size);
      im.setMatrixAt(i++, m4);
    }
    g.add(im);
  }
  return g;
}

const FONT = {
  '0': ['###', '#.#', '#.#', '#.#', '###'], '1': ['.#.', '##.', '.#.', '.#.', '###'], '2': ['###', '..#', '###', '#..', '###'],
  '3': ['###', '..#', '.##', '..#', '###'], '4': ['#.#', '#.#', '###', '..#', '..#'], '5': ['###', '#..', '###', '..#', '###'],
  '6': ['###', '#..', '###', '#.#', '###'], '7': ['###', '..#', '.#.', '.#.', '.#.'], '8': ['###', '#.#', '###', '#.#', '###'],
  '9': ['###', '#.#', '###', '..#', '###'],
};
// Pixel digits as voxels (in-world LED numerals, like the 2D DOT code read-out).
export function voxelDigits(str, col, opts = {}) {
  const rows = ['', '', '', '', ''];
  [...str].forEach((ch, i) => FONT[ch].forEach((r, y) => { rows[y] += (i ? '.' : '') + r; }));
  return voxelSprite(rows, { '#': [col, true] }, opts);
}

// 32x32-or-smaller canvas texture, nearest-filtered so texels stay hard pixel blocks.
export function pixTex(w, h, draw, repeat = [1, 1]) {
  if (w > 32 || h > 32) throw new Error('pix3d textures are capped at 32x32');
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'));
  const t = new THREE.CanvasTexture(c); t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
export const hex = c => '#' + c.toString(16).padStart(6, '0');
