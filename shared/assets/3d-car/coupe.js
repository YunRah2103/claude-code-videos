// Original rear-engine sports coupe, built procedurally (no brand, badge, logo or plate text).
//   import { buildCoupe } from '.../3d-car/coupe.js';
//   const car = buildCoupe(THREE, mat);          // mat(id, opts) -> Material (toon.js mat, or stdMat for glTF)
//   scene.add(car.group); car.pose({ spin, squat, steer, xray }); car.anchor('engine') -> world Vector3
// Units: metres, +x = front, +y = up, z = lateral. Wheelbase 2.45 m, engine block behind the rear axle.
// Body: a loft of ~150 cross-sections (each a smoothed 18-point section with wheel-arch cut-outs) driven by
// side/plan profile curves, so the silhouette stays smooth at 360x640. Glass, liners, lights are material groups.
import { ID } from './toon.js';
import { RoundedBoxGeometry } from '../vendor/jsm/geometries/RoundedBoxGeometry.js';

export const DIM = { L: 4.3, xF: 1.27, xR: -1.18, rF: 0.35, rR: 0.36, wF: 0.235, wR: 0.32, zF: 0.73, zR: 0.79 };

// monotone cubic through (x, y) knots
function curve(k) {
  const n = k.length, m = k.map((_, i) => {
    if (i === 0) return (k[1][1] - k[0][1]) / (k[1][0] - k[0][0]);
    if (i === n - 1) return (k[n - 1][1] - k[n - 2][1]) / (k[n - 1][0] - k[n - 2][0]);
    const a = (k[i][1] - k[i - 1][1]) / (k[i][0] - k[i - 1][0]), b = (k[i + 1][1] - k[i][1]) / (k[i + 1][0] - k[i][0]);
    return a * b <= 0 ? 0 : 2 / (1 / a + 1 / b);
  });
  return x => {
    if (x <= k[0][0]) return k[0][1]; if (x >= k[n - 1][0]) return k[n - 1][1];
    let i = 0; while (x > k[i + 1][0]) i++;
    const h = k[i + 1][0] - k[i][0], t = (x - k[i][0]) / h, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * k[i][1] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * k[i + 1][1] + (t3 - t2) * h * m[i + 1];
  };
}

// side + plan profiles (x from tail -2.15 to nose +2.15)
const BELT = curve([[-2.15, 0.70], [-1.95, 0.80], [-1.55, 0.86], [-1.15, 0.88], [-0.6, 0.80], [0.2, 0.775], [0.85, 0.79], [1.27, 0.80], [1.8, 0.71], [2.15, 0.57]]);
const HALFW = curve([[-2.15, 0.80], [-1.9, 0.89], [-1.2, 0.955], [-0.55, 0.87], [0.3, 0.855], [1.27, 0.885], [1.85, 0.83], [2.15, 0.70]]);
const BOT = curve([[-2.15, 0.33], [-1.95, 0.22], [1.85, 0.20], [2.15, 0.30]]);
const TOP = curve([[-2.15, 0.70], [-2.0, 0.80], [-1.75, 0.84], [-1.35, 0.92], [-0.8, 1.10], [-0.25, 1.245], [0.12, 1.255], [0.45, 1.15],
  [0.95, 0.80], [1.3, 0.745], [1.75, 0.66], [2.05, 0.56], [2.15, 0.48]]);
const CAB = curve([[-1.75, 0], [-1.25, 1], [0.7, 1], [1.0, 0]]);   // greenhouse weight
const ARCH_R = 0.425;

function archTop(x) {
  let a = -1;
  for (const [xw, r] of [[DIM.xF, DIM.rF], [DIM.xR, DIM.rR]]) {
    const d = Math.abs(x - xw), R = ARCH_R + (r - DIM.rF);
    if (d < R) a = Math.max(a, r + Math.sqrt(R * R - d * d) * 0.97);
  }
  return a;
}

// half section control points [z, y, sharp] for station x (P0 bottom centre .. P9 top centre)
function half(x) {
  const W = HALFW(x), bot = BOT(x), belt = BELT(x), top = TOP(x), c = CAB(x), a = archTop(x);
  const h = belt - bot, ay = Math.max(bot + 0.004, a);
  const p3y = Math.min(Math.max(bot + 0.55 * h, a + 0.012), belt - 0.035);
  const p2y = Math.min(Math.max(bot + 0.12 * h, a + 0.004), p3y - 0.006);
  const L = (u, v) => u + (v - u) * c;
  return [
    [0, bot, 0], [0.6 * W, bot, 1], [0.6 * W, ay, 1], [0.955 * W, p2y, a > bot ? 1 : 0], [W, p3y, 0], [0.975 * W, belt - 0.018, 0],
    [0.9 * W, belt + 0.012, 0], [L(0.8, 0.79) * W, L(belt + 0.004, belt + 0.035), 0],        // glass base (window sill)
    [L(0.52, 0.71) * W, L((belt + top) / 2 + 0.006, top - 0.085), 0],                              // near-upright side glass
    [L(0.25, 0.5) * W, top - L(0.003, 0.012), 0], [0, top, 0]];
}
// edge h (between half points h and h+1) -> what it is
const H_UNDER = [0, 1, 2], H_SIDEGLASS = 7, H_TOP = [8, 9];   // edge h joins half points h and h+1
const N_HALF = 11, K = 4;                            // control points per half, samples per edge

function ring(x) {
  const hp = half(x), pts = [...hp, ...hp.slice(1, N_HALF - 1).reverse().map(([z, y, s]) => [-z, y, s])];
  const n = pts.length, out = [];
  for (let e = 0; e < n; e++) {
    const p0 = pts[(e - 1 + n) % n], p1 = pts[e], p2 = pts[(e + 1) % n], p3 = pts[(e + 2) % n];
    const lin = p1[2] || p2[2];
    for (let s = 0; s < K; s++) {
      const t = s / K;
      if (lin) { out.push([p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t]); continue; }
      const t2 = t * t, t3 = t2 * t, f = (a, b, c2, d) => 0.5 * (2 * b + (-a + c2) * t + (2 * a - 5 * b + 4 * c2 - d) * t2 + (-a + 3 * b - 3 * c2 + d) * t3);
      out.push([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]);
    }
  }
  return out;                                         // n*K points, edge e covers indices e*K .. e*K+K
}
const N_EDGES = 2 * N_HALF - 2;
const halfEdge = e => (e < N_HALF - 1 ? e : N_EDGES - 1 - e);

function faceId(x, e) {
  const h = halfEdge(e);
  if (H_UNDER.includes(h)) return ID.DARK;
  if (h === H_SIDEGLASS && x > -1.02 && x < 0.66 && !(x > -0.36 && x < -0.29)) return ID.GLASS;     // side windows + B-pillar
  if (H_TOP.includes(h) && ((x > 0.47 && x < 0.93) || (x > -1.12 && x < -0.62))) return ID.GLASS;  // windscreen, small rear glass
  return ID.BODY;
}

function bodyGeometry(THREE) {
  const NS = 150, X0 = -2.15, X1 = 2.15, rows = [];
  for (let i = 0; i <= NS; i++) {
    const u = i / NS, x = X0 + (X1 - X0) * (0.6 * (0.5 - 0.5 * Math.cos(Math.PI * u)) + 0.4 * u);   // denser at the ends
    // rounded ends: shrink the section toward its centre over the last 18 cm (nose) / 12 cm (tail)
    let s = 1;
    if (x > 1.97) s = Math.cbrt(Math.max(0, 1 - ((x - 1.97) / 0.18) ** 3));
    if (x < -2.03) s = Math.cbrt(Math.max(0, 1 - ((-2.03 - x) / 0.12) ** 3));
    const cy = (BOT(x) + BELT(x)) / 2;
    rows.push({ x, pts: ring(x).map(([z, y]) => [z * s, cy + (y - cy) * Math.pow(s, 0.8)]) });
  }
  const M = rows[0].pts.length, pos = [], groups = {};
  for (const r of rows) for (const [z, y] of r.pts) pos.push(r.x, y, z);
  const capA = pos.length / 3; pos.push(rows[0].x, (BOT(X0) + BELT(X0)) / 2, 0);
  const capB = pos.length / 3; pos.push(rows[NS].x, (BOT(X1) + BELT(X1)) / 2, 0);
  const tri = (id, a, b, c) => (groups[id] ||= []).push(a, b, c);
  for (let i = 0; i < NS; i++) for (let j = 0; j < M; j++) {
    const a = i * M + j, b = i * M + (j + 1) % M, c = (i + 1) * M + j, d = (i + 1) * M + (j + 1) % M;
    const id = faceId((rows[i].x + rows[i + 1].x) / 2, Math.floor(j / K));
    tri(id, a, c, b); tri(id, b, c, d);
  }
  for (let j = 0; j < M; j++) { tri(ID.BODY, capA, j, (j + 1) % M); tri(ID.BODY, capB, NS * M + (j + 1) % M, NS * M + j); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const idx = [], ids = Object.keys(groups).map(Number);
  ids.forEach((id, gi) => { g.addGroup(idx.length, groups[id].length, gi); idx.push(...groups[id]); });
  g.setIndex(idx); g.computeVertexNormals();
  return { g, ids };
}

function wheel(THREE, mat, r, w, front) {
  const grp = new THREE.Group(), spin = new THREE.Group(); grp.add(spin);
  const rr = r * 0.72, prof = [];                     // tyre: lathe of a rounded section (sidewall bulge, flat tread)
  const N = 10;
  for (let i = 0; i <= N; i++) { const a = -Math.PI / 2 + Math.PI * i / N; prof.push(new THREE.Vector2(rr + (r - rr) * (0.55 + 0.45 * Math.cos(a)) + 0.012 * Math.cos(a) ** 8, w / 2 * Math.sin(a) * (0.92 + 0.08 * Math.cos(a)))); }
  const tyre = new THREE.Mesh(new THREE.LatheGeometry(prof, 36), mat(ID.TYRE, { spec: 0.1 })); tyre.rotation.x = Math.PI / 2;
  spin.add(tyre);
  const out = w / 2 - 0.035;
  const barrel = new THREE.Mesh(new THREE.CylinderGeometry(rr * 0.98, rr * 0.98, w * 0.8, 28, 1, true), mat(ID.DARK, { side: 2 }));
  barrel.rotation.x = Math.PI / 2; spin.add(barrel);
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(rr * 0.78, rr * 0.78, 0.03, 24), mat(ID.METAL, { level: 0.45 }));
  disc.rotation.x = Math.PI / 2; disc.position.z = out - 0.11; grp.add(disc);   // dark brake disc: spoke gaps read as gaps
  const cal = new THREE.Mesh(new RoundedBoxGeometry(0.1, 0.2, 0.07, 2, 0.03), mat(ID.TAIL, { spec: 0.5 }));   // red caliper (does not spin)
  cal.position.set(front ? -rr * 0.55 : rr * 0.55, rr * 0.3, out - 0.08); cal.rotation.z = front ? 0.5 : -0.5; grp.add(cal);
  const lip = new THREE.Mesh(new THREE.TorusGeometry(rr * 0.96, 0.024, 6, 36), mat(ID.RIM, { spec: 1.0, level: 1.15 })); lip.position.z = out; spin.add(lip);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(rr * 0.2, rr * 0.24, 0.05, 12), mat(ID.RIM, { spec: 0.8 }));
  hub.rotation.x = Math.PI / 2; hub.position.z = out - 0.01; spin.add(hub);
  for (let k = 0; k < 5; k++) {                       // 5 split spokes, tapered, slightly dished
    for (const off of [-0.11, 0.11]) {
      const sp = new THREE.Mesh(new THREE.BoxGeometry(rr * 0.78, 0.034, 0.03), mat(ID.RIM, { spec: 0.8 }));
      const a = k * Math.PI * 2 / 5 + off;
      sp.position.set(Math.cos(a) * rr * 0.55, Math.sin(a) * rr * 0.55, out - 0.025); sp.rotation.z = a; spin.add(sp);
    }
  }
  const nut = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.06, 8), mat(ID.METAL, { spec: 0.6 }));
  nut.rotation.x = Math.PI / 2; nut.position.z = out + 0.01; spin.add(nut);
  const tyreMats = [tyre.material];
  return { grp, spin, tyreMats };
}

export function buildCoupe(THREE, mat) {
  const group = new THREE.Group(), sprung = new THREE.Group(), shell = new THREE.Group(), inner = new THREE.Group();
  group.add(sprung); sprung.add(shell, inner);
  const { g, ids } = bodyGeometry(THREE);
  const body = new THREE.Mesh(g, ids.map(id => mat(id, { spec: id === ID.GLASS ? 0.9 : id === ID.BODY ? 0.45 : 0 }))); shell.add(body);

  const ray = new THREE.Raycaster(), hit = (o, d) => { ray.set(new THREE.Vector3(...o), new THREE.Vector3(...d).normalize()); return ray.intersectObject(body)[0]; };
  body.updateMatrixWorld(true);
  const stick = (mesh, o, d, lift = 0.004, upright = false) => {   // place a part flush on the body surface, facing out
    const h = hit(o, d); if (!h) return null;
    const n = upright ? new THREE.Vector3(...d).negate().normalize() : h.face.normal.clone(); mesh.position.copy(h.point).addScaledVector(n, lift);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), n); shell.add(mesh); return h;
  };

  // round headlights with a bezel and an inner lens ring
  for (const s of [1, -1]) {
    const lamp = new THREE.Group();
    lamp.add(new THREE.Mesh(new THREE.CircleGeometry(0.13, 24), mat(ID.HEAD, { kind: 0, spec: 0.6, level: 0.7 })));   // dark lens
    const bez = new THREE.Mesh(new THREE.TorusGeometry(0.135, 0.02, 6, 28), mat(ID.RIM, { spec: 0.8 })); lamp.add(bez);
    const drl = new THREE.Mesh(new THREE.TorusGeometry(0.085, 0.016, 4, 24), mat(ID.HEAD, { kind: 3, level: 1.25 })); drl.position.z = 0.004; lamp.add(drl);
    const core = new THREE.Mesh(new THREE.CircleGeometry(0.032, 12), mat(ID.HEAD, { kind: 3, level: 0.95 })); core.position.z = 0.006; lamp.add(core);
    stick(lamp, [3, 0.62, s * 0.6], [-1, 0, 0], 0.012);
    const ind = new THREE.Mesh(new RoundedBoxGeometry(0.16, 0.04, 0.03, 2, 0.015), mat(ID.TAIL, { kind: 3, level: 1.1 }));   // slim side lamp
    stick(ind, [3, 0.5, s * 0.68], [-1, 0, 0], 0.0, true);
    const duct = new THREE.Mesh(new RoundedBoxGeometry(0.26, 0.09, 0.05, 2, 0.04), mat(ID.DARK)); stick(duct, [3, 0.36, s * 0.47], [-1, 0, 0], 0.0, true);
  }
  const mouth = new THREE.Mesh(new RoundedBoxGeometry(0.36, 0.07, 0.05, 2, 0.03), mat(ID.DARK)); stick(mouth, [3, 0.34, 0], [-1, 0, 0], 0.0, true);
  const lip = new THREE.Mesh(new RoundedBoxGeometry(0.08, 0.03, 1.4, 2, 0.012), mat(ID.DARK)); lip.position.set(2.0, 0.22, 0); shell.add(lip);

  // taillight bar: tube through surface points across the tail
  const tp = [];
  for (let i = 0; i <= 12; i++) { const z = -0.74 + 1.48 * i / 12, h = hit([-3, 0.69, z], [1, 0, 0]); if (h) tp.push(h.point.clone().add(new THREE.Vector3(-0.012, 0, 0))); }
  if (tp.length > 3) shell.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(tp), 40, 0.028, 6), mat(ID.TAIL, { spec: 0.6, glow: 0.1 })));
  // rear diffuser + twin exhaust tips
  const diff = new THREE.Mesh(new RoundedBoxGeometry(0.12, 0.12, 1.2, 2, 0.03), mat(ID.DARK)); diff.position.set(-2.1, 0.3, 0); shell.add(diff);
  for (const s of [1, -1]) {
    const ex = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.07, 0.24, 16, 1, true), mat(ID.METAL, { spec: 1.0, side: 2, level: 1.1 }));
    ex.rotation.z = Math.PI / 2; ex.position.set(-2.15, 0.3, s * 0.2); shell.add(ex);
    const inner2 = new THREE.Mesh(new THREE.CircleGeometry(0.06, 12), mat(ID.DARK)); inner2.rotation.y = -Math.PI / 2; inner2.position.set(-2.22, 0.3, s * 0.2); shell.add(inner2);
  }
  // duck-tail spoiler: extruded side profile with a gentle bevel
  const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(-0.36, 0); sh.quadraticCurveTo(-0.42, 0.02, -0.44, 0.115); sh.lineTo(-0.40, 0.125); sh.quadraticCurveTo(-0.2, 0.07, 0, 0.03); sh.lineTo(0, 0);
  const sg = new THREE.ExtrudeGeometry(sh, { depth: 1.56, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.02, bevelSegments: 3, curveSegments: 8, steps: 24 });
  sg.translate(0, 0, -0.78);
  const sa = sg.attributes.position;                  // taper the lip into the body toward both shoulders
  for (let i = 0; i < sa.count; i++) {
    const f = Math.max(0, 1 - Math.pow(Math.abs(sa.getZ(i)) / 0.82, 3));
    sa.setY(i, sa.getY(i) * (0.25 + 0.75 * f) - (1 - f) * 0.07);
  }
  sg.computeVertexNormals();
  const sp = new THREE.Mesh(sg, mat(ID.BODY, { spec: 0.45 }));
  sp.position.set(-1.74, TOP(-1.85) - 0.07, 0); shell.add(sp);
  // engine-lid louvres (between rear glass and spoiler)
  for (let i = 0; i < 6; i++) {
    const x = -1.2 - i * 0.075, lv = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.02, 0.62), mat(ID.DARK));
    lv.position.set(x, TOP(x) + 0.005, 0); lv.rotation.z = Math.atan2(TOP(x + 0.01) - TOP(x - 0.01), 0.02); shell.add(lv);
  }
  // mirrors on short stalks
  for (const s of [1, -1]) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 10), mat(ID.BODY, { spec: 0.45 })); m.scale.set(0.15, 0.055, 0.07);
    m.position.set(0.6, BELT(0.62) + 0.09, s * (HALFW(0.62) * 0.8 + 0.12)); m.rotation.y = s * 0.15; shell.add(m);
    const glass = new THREE.Mesh(new THREE.CircleGeometry(0.055, 12), mat(ID.GLASS, { spec: 1 })); glass.scale.set(1, 0.9, 1);
    glass.rotation.y = -Math.PI / 2; glass.position.set(0.545, m.position.y, m.position.z); shell.add(glass);
    const st = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.025, 0.14), mat(ID.BODY)); st.position.set(0.63, BELT(0.62) + 0.05, s * (HALFW(0.62) * 0.8 + 0.04)); shell.add(st);
  }
  // door shut line + handle (dark slits)
  for (const s of [1, -1]) {
    for (const [x, h, tilt] of [[0.62, 0.42, -0.12], [-0.62, 0.40, 0.05]]) {   // door front / rear cut lines
      const dl = new THREE.Mesh(new THREE.BoxGeometry(0.018, h, 0.012), mat(ID.DARK)); dl.rotation.z = tilt; stick(dl, [x, 0.55, s * 2], [0, 0, -s], 0.002);
    }
    const hd = new THREE.Mesh(new RoundedBoxGeometry(0.15, 0.035, 0.014, 2, 0.007), mat(ID.DARK)); stick(hd, [-0.42, 0.71, s * 2], [0, 0, -s], 0.003);
    const intake = new THREE.Group();                 // engine air intake ahead of the rear wheel (a rear-engine cue)
    const scoop = new THREE.Mesh(new RoundedBoxGeometry(0.42, 0.13, 0.05, 3, 0.05), mat(ID.DARK)); intake.add(scoop);
    for (let k = 0; k < 3; k++) { const fin = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.012, 0.055), mat(ID.METAL, { level: 0.8 })); fin.position.y = -0.04 + k * 0.04; intake.add(fin); }
    intake.rotation.z = 0.12; stick(intake, [-0.8, 0.6, s * 2], [0, 0, -s], 0.004);
    const sill = new THREE.Mesh(new RoundedBoxGeometry(1.5, 0.07, 0.04, 2, 0.02), mat(ID.DARK)); stick(sill, [0.05, 0.27, s * 2], [0, 0, -s], 0.0, true);
  }

  // x-ray internals: chassis floor, flat engine BEHIND the rear axle, gearbox ahead of it, axles, driveshafts
  const glow = [];
  const floor = new THREE.Mesh(new RoundedBoxGeometry(3.6, 0.05, 1.3, 2, 0.02), mat(ID.DARK)); floor.position.set(0.05, 0.24, 0); inner.add(floor);
  const blockM = mat(ID.GLOW, { spec: 0.6, glow: 0.3 }); glow.push(blockM);
  const block = new THREE.Mesh(new RoundedBoxGeometry(0.62, 0.3, 0.52, 3, 0.05), blockM); block.position.set(-1.68, 0.47, 0); inner.add(block);
  for (const s of [1, -1]) {                          // opposed cylinder banks + finned heads
    const bank = new THREE.Mesh(new RoundedBoxGeometry(0.56, 0.22, 0.2, 2, 0.04), blockM); bank.position.set(-1.68, 0.44, s * 0.35); inner.add(bank);
    const head = new THREE.Mesh(new RoundedBoxGeometry(0.58, 0.18, 0.08, 2, 0.03), mat(ID.METAL, { spec: 0.6 })); head.position.set(-1.68, 0.44, s * 0.49); inner.add(head);
    for (let k = 0; k < 3; k++) { const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.25, 8), mat(ID.METAL)); pipe.position.set(-1.86 + k * 0.17, 0.32, s * 0.4); pipe.rotation.x = s * 0.6; inner.add(pipe); }
  }
  const plenum = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.5, 14), mat(ID.METAL, { spec: 0.8 })); plenum.rotation.z = Math.PI / 2; plenum.position.set(-1.68, 0.68, 0); inner.add(plenum);
  const fan = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.06, 16), mat(ID.METAL, { spec: 0.6 })); fan.position.set(-1.68, 0.72, 0); inner.add(fan);
  const gbox = new THREE.Mesh(new RoundedBoxGeometry(0.62, 0.24, 0.3, 2, 0.05), mat(ID.METAL, { spec: 0.5 })); gbox.position.set(-1.05, 0.38, 0); inner.add(gbox);
  const axM = mat(ID.METAL, { spec: 0.8, level: 1.1 }), axles = { rear: [], front: [] };
  for (const s of [1, -1]) {
    const ds = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, DIM.zR - 0.12, 10), axM); ds.rotation.x = Math.PI / 2; ds.position.set(DIM.xR, DIM.rR, s * (DIM.zR / 2 + 0.06)); inner.add(ds); axles.rear.push(ds);
    const cv = new THREE.Mesh(new THREE.SphereGeometry(0.06, 10, 8), axM); cv.position.set(DIM.xR, DIM.rR, s * 0.18); inner.add(cv);
  }
  const fa = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, DIM.zF * 2 - 0.2, 10), axM); fa.rotation.x = Math.PI / 2; fa.position.set(DIM.xF, DIM.rF, 0); inner.add(fa); axles.front.push(fa);
  const tank = new THREE.Mesh(new RoundedBoxGeometry(0.5, 0.2, 0.8, 2, 0.05), mat(ID.METAL, { level: 0.7 })); tank.position.set(1.0, 0.4, 0); inner.add(tank);
  const seat = new THREE.Mesh(new RoundedBoxGeometry(0.45, 0.5, 0.45, 2, 0.08), mat(ID.DARK)); for (const s of [1, -1]) { const c2 = seat.clone(); c2.position.set(-0.3, 0.55, s * 0.36); c2.rotation.z = -0.25; inner.add(c2); }
  const wheelArc = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.02, 6, 20), mat(ID.DARK)); wheelArc.position.set(0.25, 0.85, 0.36); wheelArc.rotation.y = Math.PI / 2; wheelArc.rotation.x = 0.4; inner.add(wheelArc);
  inner.visible = false;

  const wheels = [];
  for (const [x, r, w, z, front] of [[DIM.xF, DIM.rF, DIM.wF, DIM.zF, 1], [DIM.xR, DIM.rR, DIM.wR, DIM.zR, 0]]) for (const s of [1, -1]) {
    const wh = wheel(THREE, mat, r, w, front); wh.grp.position.set(x, r, s * z); if (s < 0) wh.grp.rotation.y = Math.PI;
    wh.side = s; wh.front = front; group.add(wh.grp); wheels.push(wh);
  }

  const A = { engine: [-1.68, 0.55, 0], rear_axle: [DIM.xR, DIM.rR, 0.45], front_axle: [DIM.xF, DIM.rF, 0], rear_tyre: [DIM.xR, DIM.rR, DIM.zR + 0.12],
    rear_tyre_l: [DIM.xR, DIM.rR, -DIM.zR - 0.12], front_tyre: [DIM.xF, DIM.rF, DIM.zF + 0.1], headlight: [1.95, 0.66, 0.6], tail: [-2.15, 0.7, 0], roof: [0, 1.22, 0] };
  const hotMat = mat(ID.HOT, { spec: 0.1, glow: 0.2 });
  function pose({ spin = 0, squat = 0, roll = 0, steer = 0, xray = false, hot = 0, glowPulse = 0 } = {}) {
    sprung.rotation.z = squat; sprung.position.y = -Math.abs(squat) * 0.6; sprung.rotation.x = roll;
    for (const w of wheels) {
      w.spin.rotation.z = -spin * w.side * (w.front ? DIM.rR / DIM.rF : 1);
      w.grp.rotation.y = (w.side < 0 ? Math.PI : 0) + (w.front ? steer : 0);
      w.spin.children[0].material = (!w.front && hot > 0.5) ? hotMat : w.tyreMats[0];
    }
    shell.visible = true; inner.visible = !!xray;
    for (const m of glow) if (m.uniforms) m.uniforms.uGlow.value = 0.3 + glowPulse;
  }
  const v = new THREE.Vector3();
  const anchor = (name) => { const p = A[name]; v.set(...p); (name.includes('tyre') ? group : sprung).localToWorld(v); return v.clone(); };
  return { group, sprung, shell, inner, wheels, pose, anchor, ANCHORS: A, body };
}
