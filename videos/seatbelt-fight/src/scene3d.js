// seatbelt-fight v2: 3D dusk street (Three.js), solid limb figures, one continuous scene.
// 0-3 fight | 2.78 spinning back kick sends him flying | 3.0-3.6 he dives into the parked car | belted, launch
// 5.0 the car hits the barrier: freeze, record scratch, push in to the locked belt | 5.25 "Quick pause."
// 6.1-13.1 explainer (camera keeps orbiting, he breathes and gestures) | 13.1 time resumes: force limiter, airbag, he's fine
// 16.2 whip pan back to the street | 16.55 last hit | 16.9 "Did you know that?" + poll | 18.0 = frame 1 (loop).
import * as THREE from 'three';
import { buildStreet, barrier } from '../../../shared/assets/street3d/world.js';
import { makeFigure } from '../../../shared/assets/street3d/figure.js';
import { makeCar } from '../../../shared/assets/street3d/car.js';
import { makeStage } from '../../../shared/assets/street3d/stage.js';
const S = {}; let WORDS = [], LOUD = [], CH = [];
const HS = 1 / 60;
const hold = (t, n) => [t + n * HS, {}, 'l'];
const CAR0 = -6.5, CARZ = -3.2, BARX = -27, CRASHX = BARX + .35 + 2.12, T_GO = 4.0, T_CRASH = 5.0, T_FREEZE = 5.05, T_RESUME = 13.1, T_IN = 3.6;
// ---------- fighters ----------
const G0 = { x: -.9, z: 0, y: 0, face: 1, lean: 8, head: -4, a1: 35, a2: 115, b1: 55, b2: 120, l1: 22, l2: -18, m1: -20, m2: 12, turn: 0, rot: 0, yaw: 0, sx: 1, sy: 1 };
const R0 = Object.assign({}, G0, { x: .9, face: -1, lean: 10, a1: 40, a2: 110, b1: 58, b2: 116 });
const BLOCK = { a1: 75, a2: 128, b1: 85, b2: 122 };
const CROUCH = { l1: 62, l2: -110, m1: -8, m2: -74 };
const g = K.track([
  [0, G0],
  [.25, { x: -.82, lean: 11 }, 'io'],                                                                   // weight forward
  [.38, { x: -.88, lean: -2, head: -8 }, 'io'],
  [.46, { lean: -16, head: -18, a1: 62, a2: 122, b1: 72, b2: 120 }, 'o'],                               // slips the jab
  [.70, Object.assign({}, G0, { x: -.82 }), 'io'],
  [.78, { lean: 2, a1: 22, a2: 128 }, 'io'],                                                             // cocks the jab
  [.86, { x: -.6, lean: 22, a1: 90, a2: 6, l1: 34, l2: -10, m1: -32, m2: 4 }, 'o'], hold(.86, 2),       // jab (blocked)
  [1.0, Object.assign({}, G0, { x: -.62, lean: 6 }), 'io'],
  [1.28, { x: -.66, lean: -22, l1: 96, l2: -126, m1: -14, m2: 6, a1: 62, a2: 104, b1: -18, b2: 60 }, 'io'], // slow chamber
  [1.40, { x: -.42, lean: -30, l1: 98, l2: -2, m1: -6, m2: -8, a1: -38, a2: 30, b1: 118, b2: 22 }, 'o'], hold(1.40, 3), // roundhouse
  [1.62, { l1: 62, l2: -104, lean: -6, a1: 40, a2: 110, b1: 55, b2: 120 }, 'io'],                      // retract
  [1.80, Object.assign({}, G0, { x: -.45 }), 'io'],
  [1.97, { x: -.42, lean: 12 }],
  [2.07, Object.assign({ x: -.4, lean: 38, head: 12, a1: 30, a2: 130, b1: 40, b2: 120 }, CROUCH), 'o'],  // ducks the hook
  [2.18, { lean: 30, a1: 10, a2: 140 }, 'io'],
  [2.28, { y: .05, lean: 2, head: -6, a1: 166, a2: 18, l1: 26, l2: -10, m1: -24, m2: 6 }, 'o'], hold(2.28, 2), // uppercut (blocked)
  [2.44, Object.assign({}, G0, { x: -.38 }), 'io'],
  [2.64, Object.assign({ x: -.4, lean: 4 }, BLOCK), 'io'],
  [2.78, { x: -.46, lean: -34, head: -20, sx: .94 }, 'o'], hold(2.78, 3),                                // takes the back kick
  [2.78 + 3 * HS + .001, { ya: .9 }, 'h'],
  [3.04, { x: -2.3, z: -.7, ya: 1.45, sx: 1, lean: -55, head: -12, l1: 34, l2: -40, m1: 10, m2: -60, a1: 150, a2: 30, b1: 125, b2: 40 }, 'o'], // knocked flying
  [3.16, { x: -3.3, z: -1.2, ya: 1.6, lean: -20, l1: 70, l2: -110, m1: 60, m2: -110, a1: 90, a2: 70, b1: 90, b2: 70 }, 'io'],          // tucks
  [3.26, { x: -4.3, z: -1.7, ya: 1.62, yaw: 155, lean: 60, head: -10, a1: 165, a2: 5, b1: 160, b2: 5, l1: -20, l2: -10, m1: -12, m2: -20 }, 'io'], // twists to face the car
  [3.58, { x: -5.95, z: -2.55, ya: 1.25, lean: 86, head: -14, sx: 1.08, sy: .94 }, 'i'],                                             // head-first through the window
  [3.62, { ya: 0 }, 'h'],
  // back in the street (whip pan hides the jump)
  [16.18, Object.assign({}, G0, { ya: 0, x: -2.2, lean: 28, a1: -10, a2: 130, b1: 90, b2: 70, l1: 60, l2: -40, m1: -50, m2: -50 })],
  [16.42, { x: -.75, l1: -30, l2: -40, m1: 50, m2: -50, a1: 12, a2: 140, lean: 20 }, 'l'],
  [16.55, { x: -.5, lean: 26, a1: 82, a2: 4, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8, head: -4 }, 'o'], hold(16.55, 3),
  [16.72, { lean: 10, a1: 55, a2: 60 }, 'io'],
  [16.95, { x: -.7, lean: 0, head: 0, turn: 1, a1: 30, a2: 70, b1: 22, b2: 40, l1: 12, l2: -6, m1: -12, m2: 6 }, 'io'],
  [17.2, { b1: 60, b2: 100 }], [17.5, {}],
  [17.62, { turn: 0 }, 'io'], [17.93, Object.assign({}, G0)], [18.2, Object.assign({}, G0)],
]);
const r = K.track([
  [0, R0],
  [.25, { x: .82, lean: 5 }, 'io'],
  [.38, { x: .84, lean: 0, a1: 20, a2: 132 }, 'io'],                                                     // winds the jab
  [.46, { x: .62, lean: 22, a1: 90, a2: 4 }, 'o'],
  [.64, { x: .74, lean: 10, a1: 40, a2: 110 }, 'io'],
  [.86, Object.assign({ x: .76, lean: -6 }, BLOCK), 'o'], hold(.86, 2),
  [1.05, Object.assign({}, R0, { x: .78 }), 'io'],
  [1.30, Object.assign({ x: .8, lean: 0 }, BLOCK), 'io'],
  [1.40, { x: .86, lean: -18, head: -16, sx: .95 }, 'o'], hold(1.40, 3),                               // eats the roundhouse
  [1.68, { x: 1.3, lean: -6, head: -4, sx: 1, l1: 34, l2: -36, m1: -26, m2: 4 }, 'o'],                  // slides back
  [1.86, Object.assign({}, R0, { x: 1.2 }), 'io'],
  [1.97, { x: 1.0, lean: 4, a1: 30, a2: 124, yaw: 15 }, 'io'],                                           // loads the hook
  [2.08, { x: .72, lean: 26, a1: 96, a2: 78, yaw: -25 }, 'o'],
  [2.22, { lean: 8, a1: 42, a2: 108, yaw: 0 }, 'io'],
  [2.28, Object.assign({ x: .74, lean: -8, head: -6 }, BLOCK), 'o'], hold(2.28, 2),
  [2.44, Object.assign({}, R0, { x: .8 }), 'io'],
  [2.56, { x: .82, lean: 6, yaw: 70, l1: 40, l2: -60 }, 'i'],                                             // spins
  [2.68, { yaw: 180, lean: 26, l1: -60, l2: -110, a1: 20, a2: 90, b1: 30, b2: 90 }, 'l'],
  [2.78, { x: .7, yaw: 182, lean: 40, l1: -98, l2: -2, m1: 14, m2: -14 }, 'o'], hold(2.78, 3),           // back kick
  [3.0, { yaw: 300, lean: 10, l1: 30, l2: -40, m1: -18, m2: 12, x: .75 }, 'io'],
  [3.16, Object.assign({}, R0, { x: .75, yaw: 360 }), 'io'], [3.161, { yaw: 0 }, 'h'],
  [T_RESUME, {}], [16.3, Object.assign({}, R0)],
  [16.55, { lean: -30, head: -24, sx: .94 }, 'o'], hold(16.55, 3),
  [16.85, { x: 2.0, y: .35, rot: -40, lean: -30, sx: 1, l1: 60, l2: -80, m1: 40, m2: -60, a1: 160, a2: 20, b1: 140, b2: 30 }, 'o'],
  [17.1, { x: 2.3, y: 0, rot: 0, lean: -18, head: 6, l1: 86, l2: -8, m1: 80, m2: -14, a1: -30, a2: 10, b1: -40, b2: 10 }, 'o'],
  [17.35, Object.assign({ x: 2.2, lean: 30, a1: 10, a2: 60 }, CROUCH), 'io'],
  [17.6, { x: 1.4, y: .5, lean: 0, l1: 50, l2: -80, m1: 20, m2: -70, a1: 130, a2: 20, b1: 120, b2: 20 }, 'o'],
  [17.82, Object.assign({}, R0, { x: .95 }), 'io'], [17.93, Object.assign({}, R0)], [18.2, Object.assign({}, R0)],
]);
// him in the car (car-local, abs; camera is on the car's local -Z side so cz = -1)
const SEAT = { abs: 1, x: -.32, y: .62, z: -.42, face: 1, cz: -1, lean: -14, head: 4, a1: 66, a2: 26, b1: 64, b2: 28, l1: 82, l2: -76, m1: 80, m2: -74, turn: 0, sx: 1, sy: 1 };
const seat = K.track([
  [T_IN, Object.assign({}, SEAT, { y: .9, lean: 40, sy: .85 })], [T_IN + .16, SEAT, 'o'],
  [T_GO, {}], [T_GO + .12, { lean: -20, head: 8 }, 'o'], [4.7, { lean: -16, head: 4 }],
  [T_CRASH, {}], [T_FREEZE, { lean: 22, head: 18, a1: 80, a2: 6, b1: 78, b2: 8 }, 'o'],
  // presenter (time frozen around him): turns to camera, breathes, gestures on the words
  [5.12, {}], [5.36, { turn: 1, head: 0, lean: 6 }, 'back'],
  [5.9, { lean: -4, b1: 120, b2: 40 }, 'io'],
  [6.6, { b1: 70, b2: 70 }], [7.1, { b1: 135, b2: 20, head: -4 }, 'o'], [7.9, { b1: 60, b2: 90, head: 3 }],
  [8.4, { b1: 120, b2: 50 }, 'o'], [9.2, { b1: 150, b2: 10, head: -5 }, 'o'], [9.9, { b1: 100, b2: 80, head: 4 }],
  [10.6, { b1: 135, b2: 30, a1: 66 }, 'o'], [11.4, { b1: 70, b2: 60, head: -3 }], [12.0, { b1: 140, b2: 20 }, 'o'], [12.8, { b1: 64, b2: 28, head: 2 }],
  [T_RESUME, { lean: -4, turn: 1 }],
  [13.45, { lean: 24, head: 16, turn: .2 }, 'io'], [13.75, { lean: 30, head: 22 }, 'o'],                 // into the airbag (belt eases a little)
  [14.4, { lean: -6, head: 0 }, 'io'], [14.9, { turn: .5, head: 12 }], [15.1, { head: -10 }], [15.3, { head: 10 }], [15.5, { head: 0, turn: 1 }],
  [15.75, { b1: 165, b2: 30 }, 'back'], [16.2, {}],
]);
// ---------- car ----------
const carX = t => t < T_GO ? CAR0 : t < T_CRASH ? CAR0 - (CAR0 - CRASHX) * Math.pow((t - T_GO) / (T_CRASH - T_GO), 1.7) : CRASHX;
const simT = t => t >= T_FREEZE && t < T_RESUME ? T_FREEZE : t;
const crushAt = t => K.ease.o(K.clamp((simT(t) - T_CRASH) / .06, 0, 1));
const pitchAt = t => { const s = simT(t);
  if (s < T_GO) return 0; if (s < T_CRASH) return -2.2 * Math.sin(Math.min(1, (s - T_GO) / .35) * Math.PI) ;
  if (s < T_RESUME) return 3.5 * K.ease.o(K.clamp((s - T_CRASH) / .05, 0, 1));
  return 3.5 * Math.exp(-(s - T_RESUME) * 3) * Math.cos((s - T_RESUME) * 9); };
const airbagAt = t => t < 13.42 ? 0 : t < 13.62 ? K.ease.back((t - 13.42) / .2) : t < 14.6 ? 1 : Math.max(0, 1 - (t - 14.6) / .55);
// ---------- impacts: ONE flash per big hit ----------
const IMP = [
  { t: .86, s: 'block' }, { t: 1.40, s: 'punch_big', big: 1 }, { t: 2.28, s: 'block' }, { t: 2.78, s: 'punch_big', big: 1 },
  { t: T_CRASH, s: 'crash', big: 1 }, { t: 16.55, s: 'punch_big', big: 1 },
];
const WHOOSH = [.42, .84, 1.36, 2.05, 2.26, 2.62, 2.74, 3.1, 16.24, 16.5];
// ---------- camera (spherical keys; cut: true = hard cut) ----------
const CAM = (t, tx, ty, tz, dist, az, el, fov, e = 'io', cut = false, blur = 4, roll = 0) => ({ t, tx, ty, tz, dist, az, el, fov, e, cut, blur, roll });
const carHead = () => [carX(simT(curT)) + .3, 1.18, CARZ + .42];
let curT = 0;
const camKeys = [
  CAM(0, 0, 1.0, 0, 6.2, 0, 6, 38), CAM(1.3, 0, 1.0, 0, 5.4, 22, 5, 38, 'io'),
  CAM(1.3, .25, 1.15, 0, 3.0, -38, 0, 36, 'io', true, 7), CAM(1.95, .1, 1.1, 0, 2.8, -52, 2, 36, 'io', false, 7),
  CAM(1.95, 0, 1.0, 0, 4.6, 30, 8, 38, 'io', true, 5), CAM(2.6, 0, 1.0, 0, 4.0, 18, 4, 38, 'io', false, 5),
  CAM(2.6, -.2, 1.15, 0, 3.2, -22, 1, 36, 'io', true, 7), CAM(2.84, -.4, 1.15, 0, 3.0, -18, 1, 36),
  CAM(3.02, -2.2, 1.5, -.6, 4.6, 18, 5, 40, 'o', false, 5), CAM(3.32, -4.3, 1.5, -1.6, 4.4, 14, 6, 40, 'io', false, 5), CAM(3.66, -6.0, 1.2, -2.7, 2.8, 8, 4, 38, 'io', false, 6),
  CAM(4.0, 'car', 0, 0, 2.3, 6, 3, 38, 'io', false, 7), CAM(4.55, 'car', 0, 0, 6.0, -38, 8, 40, 'io', false, 5),
  CAM(T_CRASH, 'car', 0, 0, 6.2, -44, 9, 40, 'io', false, 5), CAM(T_FREEZE, 'car', 0, 0, 6.2, -44, 9, 40),
  CAM(5.32, 'chest', 0, 0, 1.9, 4, 2, 36, 'io', false, 8), CAM(5.95, 'present', 0, 0, 3.7, -14, 4, 40, 'io', false, 7),
  CAM(T_RESUME, 'present', 0, 0, 3.3, 14, 4, 40, 'l', false, 7), CAM(16.0, 'present', 0, 0, 3.1, 2, 4, 40, 'io', false, 7),
  CAM(16.42, -.1, 1.1, 0, 4.4, 14, 5, 38, 'io', false, 5), CAM(16.62, .3, 1.15, 0, 3.4, -14, 2, 36, 'o', false, 6),
  CAM(17.05, -.7, 1.25, 0, 3.9, 0, 4, 38, 'io', false, 6), CAM(17.55, -.75, 1.25, 0, 3.9, 4, 4, 38),
  CAM(17.93, 0, 1.0, 0, 6.2, 0, 6, 38), CAM(18.5, 0, 1.0, 0, 6.2, 0, 6, 38),
];
function camAt(t) {
  curT = t;
  const res = k => { if (typeof k.tx === 'number') return [k.tx, k.ty, k.tz]; const c = carX(simT(t));
    if (k.tx === 'car') return [c - 1.3, 1.0, CARZ]; if (k.tx === 'chest') return [c + .25, .98, CARZ + .42]; return [c + .25, 1.75, CARZ + .42]; };
  let i = 0; while (i < camKeys.length - 1 && camKeys[i + 1].t <= t) i++;
  const a = camKeys[i], b = camKeys[Math.min(i + 1, camKeys.length - 1)];
  const u = b === a || b.cut ? 0 : K.ease[b.e]((t - a.t) / Math.max(b.t - a.t, 1e-6));
  const pa = res(a), pb = res(b), c = {};
  ['tx', 'ty', 'tz'].forEach((k, j) => c[k] = K.lerp(pa[j], pb[j], u));
  for (const k of ['dist', 'az', 'el', 'fov', 'blur', 'roll']) c[k] = K.lerp(a[k], b[k], u);
  // one short, smooth shake per big hit (decaying sine, no random offsets)
  for (const im of IMP) if (im.big) { const s = simT(t) - im.t; if (s > 0 && s < .3) { const e = Math.exp(-s * 14) * (im.s === 'crash' ? .07 : .045); c.tx += Math.sin(s * 70) * e; c.ty += Math.cos(s * 55) * e * .7; } }
  return c;
}
// ---------- overlays: diagrams, headline, captions ----------
const wordAt = w => (WORDS.find(x => x.w.toLowerCase().replace(/[^a-z']/g, '') === w) || {}).s;
function chunks() {
  const out = []; let cur = [];
  WORDS.forEach((w, i) => { cur.push(i); const end = /[.,?]$/.test(w.w) || cur.length === 3 || cur.map(k => WORDS[k].w).join(' ').length > 15; if (end) { out.push(cur); cur = []; } });
  if (cur.length) out.push(cur);
  return out.map((ix, k) => ({ ix, s: WORDS[ix[0]].s - .05, e: k + 1 < out.length ? Math.min(WORDS[out[k + 1][0]].s - .05, WORDS[ix[ix.length - 1]].e + .5) : WORDS[ix[ix.length - 1]].e + .5 }));
}
function captions(c, t) {
  const ch = CH.find(q => t >= q.s && t < q.e); if (!ch) return;
  const parts = []; ch.ix.forEach((k, j) => parts.push([WORDS[k].w.toUpperCase() + (j < ch.ix.length - 1 ? ' ' : ''), t >= WORDS[k].s - .03 ? '#ffd35f' : '#ffffff']));
  const pop = K.ease.back(K.clamp((t - ch.s) / .12, 0, 1));
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0);
  const str = parts.map(p => p[0]).join('');
  K.text(c, str, 459, 1090 + (1 - pop) * 14, { center: 1, size: 66, stroke: '#0d1424', sw: 14, parts });
  c.restore();
}
function headline(c, t) {
  const H = [[S.T.v1, S.T.v2, 'MEET THE PRETENSIONER'], [S.T.v2, S.T.v3, 'IT FIRES IN A CRASH'], [S.T.v3, S.T.v4, 'WHY SNUG MATTERS'], [S.T.v4, 15.35, 'THE FORCE LIMITER']];
  for (const [a, b, s] of H) if (t >= a && t < b) {
    const u = K.clamp((t - a) / .18, 0, 1), v = K.clamp((b - t) / .15, 0, 1);
    K.text(c, s, 459, 312 + (1 - K.ease.o(u)) * -20, { center: 1, size: 54, plate: '#ffd35f', color: '#0d1424', pad: 24, alpha: Math.min(u, v) });
  }
}
function tag(c) { K.text(c, 'Yub · cartoon', 44, 240, { size: 30, weight: 800, color: 'rgba(255,255,255,.88)', stroke: 'rgba(13,20,36,.6)', sw: 6 }); }
function label(c, s, x, y, lx, ly, col = '#ffffff') {
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.strokeStyle = 'rgba(255,255,255,.8)'; c.lineWidth = 4; c.beginPath(); c.moveTo(x + 6, y + 22); c.lineTo(lx, ly); c.stroke();
  c.fillStyle = '#fff'; c.beginPath(); c.arc(lx, ly, 8, 0, 7); c.fill(); c.restore();
  K.text(c, s, x, y, { size: 40, weight: 800, color: col, plate: 'rgba(13,20,36,.85)', pad: 14 });
}
function panel(c, t, a) {
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = a;
  const g = c.createLinearGradient(0, 200, 0, 1250); g.addColorStop(0, 'rgba(10,14,32,.92)'); g.addColorStop(.75, 'rgba(10,14,32,.85)'); g.addColorStop(1, 'rgba(10,14,32,0)');
  c.fillStyle = g; c.fillRect(0, 0, K.W, 1250);
  c.restore();
}
function belt(c, pts, slack, glow) { c.save(); if (glow) { c.shadowColor = '#ffb347'; c.shadowBlur = 26; } c.strokeStyle = K.DG.belt; c.lineWidth = 16; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); c.lineTo(pts[1][0], pts[1][1]);
  const mx = (pts[1][0] + pts[2][0]) / 2 - slack * 70, my = (pts[1][1] + pts[2][1]) / 2 + slack * 20; c.quadraticCurveTo(mx, my, pts[2][0], pts[2][1]); c.stroke(); c.restore(); }
function diagrams(c, t) {
  const T = S.T; if (t < T.v1 - .3 || t >= T.v4) return;
  const fade = K.clamp((t - (T.v1 - .3)) / .3, 0, 1) * K.clamp((T.v4 - t) / .25, 0, 1);
  panel(c, t, fade);
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = fade;
  const vs = t < T.v2 ? T.v1 : t < T.v3 ? T.v2 : T.v3, kb = .95 + .1 * K.sm((t - vs) / 2.4);
  c.translate(480, 760); c.scale(kb, kb); c.rotate(Math.sin(t * 1.3) * .012); c.translate(-480, -760);
  if (t < T.v2) {          // V1: cutaway of belt, retractor, pretensioner
    const u = K.clamp((t - T.v1) / .35, 0, 1), sl = 1 - K.ease.o(K.clamp((t - T.tighten) / .35, 0, 1));
    c.translate(0, (1 - K.ease.o(u)) * 40 - 70);
    K.seatShape(c, 300, 930, 1.05); const J = K.dummy(c, 300, 930, 1.05, 0);
    c.fillStyle = '#4a4f66'; c.beginPath(); c.roundRect(560, 470, 34, 560, 12); c.fill();
    belt(c, [[577, 520], J.shoulder, [J.hip[0] - 20, J.hip[1] + 10]], sl * .9, t > T.tighten);
    c.strokeStyle = K.DG.belt; c.lineWidth = 16; c.beginPath(); c.moveTo(577, 520); c.lineTo(577, 980); c.stroke();
    K.spool(c, 577, 1000, 44, -K.clamp((t - T.tighten) / .35, 0, 1) * 6, .8 + .2 * (1 - sl));
    K.cartridge(c, 680, 1000, .62, 0);
    c.fillStyle = '#c9ced8'; c.beginPath(); c.roundRect(560, 505, 34, 30, 8); c.fill();
    if (t > T.tighten && t < T.tighten + .5) K.arrow(c, 640, 640, 640, 900, '#ffd35f', 9);
    c.setTransform(1, 0, 0, 1, 0, 0);
    if (u > .5) { label(c, 'Retractor', 650, 760, 615, 905); label(c, 'Pretensioner', 560, 990, 690, 935, '#ffd35f'); }
  } else if (t < T.v3) {   // V2: charge fires / motor spins, spool winds in the slack
    const fire = K.clamp((t - T.charge) / .45, 0, 1), mot = K.clamp((t - T.motor) / .25, 0, 1);
    const spin = K.ease.o(K.clamp((t - T.charge) / .4, 0, 1)) * 9 + (t > T.motor ? (t - T.motor) * 10 : 0);
    c.translate(0, (1 - K.ease.o(K.clamp((t - T.v2) / .3, 0, 1))) * 40);
    if (t > T.crashW && t < T.crashW + .25) c.translate(Math.sin(t * 90) * 8, 0);
    c.strokeStyle = K.DG.belt; c.lineWidth = 34; c.lineCap = 'butt'; c.beginPath(); c.moveTo(560 + 100, 460); c.lineTo(560 + 100, 730); c.stroke();
    K.spool(c, 560, 740, 110, -spin, .6 + .4 * Math.min(1, spin / 9));
    if (spin > .5) K.arrow(c, 740, 470, 740, 640, '#ffd35f', 10);
    c.globalAlpha = fade * (1 - mot * .65); K.cartridge(c, 330, 720, 1.25, fire); c.globalAlpha = fade;
    c.globalAlpha = fade * mot; K.motor(c, 320, 930, 1.1, (t - T.motor) * 14); c.globalAlpha = fade;
    c.setTransform(1, 0, 0, 1, 0, 0);
    if (t > T.charge) label(c, 'Small charge', 70, 560, 240, 700, '#ff8a7a');
    if (t > T.motor) label(c, 'Or a motor', 90, 1010, 250, 960, '#5fe3ff');
  } else {                 // V3: tight vs loose belt in a crash pulse
    const ph = ((t - T.v3) % 1.3) / 1.3, pulse = ph < .35 ? K.ease.o(ph / .35) : 1 - K.ease.io((ph - .35) / .65);
    for (const [ox, tight] of [[70, 1], [490, 0]]) {
      c.save(); c.fillStyle = 'rgba(255,255,255,.05)'; c.beginPath(); c.roundRect(ox, 470, 400, 560, 30); c.fill();
      const lean = tight ? 5 * pulse : 32 * pulse, dx = tight ? -4 * pulse : -40 * pulse;
      K.seatShape(c, ox + 150, 960, .7); const J = K.dummy(c, ox + 150 + dx, 960, .7, lean);
      c.fillStyle = '#4a4f66'; c.fillRect(ox + 330, 560, 22, 420);
      belt(c, [[ox + 341, 600], J.shoulder, [J.hip[0] - 10, J.hip[1] + 8]], tight ? 0 : .9 + pulse * .2, tight);
      if (!tight && pulse > .6) { c.fillStyle = 'rgba(255,74,61,.9)'; c.beginPath(); c.arc(J.chest[0] - 60, J.chest[1] - 40, 16, 0, 7); c.fill(); }
      c.restore();
    }
    label(c, 'Tight belt', 110, 500, 210, 640, '#7dffb0'); label(c, 'Loose belt', 520, 500, 640, 640, '#ff8a7a');
  }
  c.restore();
}
function limiterCard(c, t) {
  const V = S.T.v4, a = K.clamp((t - V) / .3, 0, 1) * K.clamp((15.25 - t) / .3, 0, 1); if (a <= 0) return;
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = a; c.translate(0, (1 - K.ease.o(a)) * 30);
  c.fillStyle = 'rgba(10,14,32,.88)'; c.beginPath(); c.roundRect(70, 400, 820, 420, 34); c.fill();
  const pay = K.sm((t - V - .2) / .7), load = t < V + .15 ? .55 : t < V + .5 ? .55 + (t - V - .15) / .35 * .4 : .95 - K.sm((t - V - .5) / .6) * .45;
  c.strokeStyle = K.DG.belt; c.lineWidth = 30; c.beginPath(); c.moveTo(330, 440); c.lineTo(330, 610); c.stroke();
  K.spool(c, 250, 640, 80, pay * 2.2 + (t - V) * .2, .9 - pay * .15);
  if (t > V + .15 && t < V + 2) K.arrow(c, 400, 640, 400, 470, '#5fe3ff', 9);
  c.fillStyle = '#20263d'; c.beginPath(); c.roundRect(600, 450, 70, 300, 20); c.fill();
  const col = load > .8 ? '#ff4a3d' : '#7dffb0'; c.fillStyle = col; c.beginPath(); c.roundRect(610, 460 + 280 * (1 - load), 50, 280 * load, 14); c.fill();
  c.strokeStyle = 'rgba(255,255,255,.7)'; c.lineWidth = 4; c.setLineDash([10, 8]); c.beginPath(); c.moveTo(585, 460 + 280 * .1); c.lineTo(690, 460 + 280 * .1); c.stroke();
  c.restore();
  if (a > .5) { K.text(c, 'Belt pays out', 110, 750, { size: 38, weight: 800, color: '#5fe3ff' }); K.text(c, 'Chest load', 560, 760, { size: 38, weight: 800, color: col }); }
}

const blinkAt = t => ((t * 1000) % 3100) < 110;
// ---------- build ----------
let st, car, gS, gC, rv;
export async function build(canvas, d) {
  WORDS = d.words; LOUD = d.loud; CH = chunks();
  st = makeStage(canvas, { subframes: 4, shutter: .5 });
  buildStreet(st.scene, { x0: -70, x1: 50 });
  st.scene.add(barrier(BARX, CARZ));
  car = makeCar({ side: -1, color: '#2a8fa8' }); st.scene.add(car.group);
  gS = makeFigure('guy'); rv = makeFigure('rival'); gC = makeFigure('guy');
  st.scene.add(gS.root, gS.shadow, rv.root, rv.shadow); car.group.add(gC.root);
  const fill = new THREE.PointLight('#ffc48a', 6, 14, 1.6); fill.position.set(-1.5, 3.2, 3); st.scene.add(fill);
  const carFill = new THREE.PointLight('#ffd7a8', 4, 6, 1.5); carFill.position.set(.2, 1.6, -1.2); car.group.add(carFill);   // soft key on him in the cabin
  S.T = { v1: wordAt('your'), tighten: wordAt('tighten'), v2: wordAt('in'), crashW: wordAt('crash'), charge: wordAt('charge'), motor: wordAt('motor'), v3: wordAt('snug') - .3, v4: wordAt('then') };
  return { events: { impacts: IMP.map(i => ({ t: i.t, s: i.s })), whoosh: WHOOSH, crash: T_CRASH, freeze: T_FREEZE, go: T_GO, click: T_IN + .25, plop: T_IN + .1,
    airbag: 13.42, land: [17.1], resume: T_RESUME, T: S.T }, frame };
}
const V = new THREE.Vector3();
function pose(t) {
  const s = simT(t);
  // car
  const cx = carX(s); car.group.position.set(cx, 0, CARZ); car.group.rotation.set(0, Math.PI, -pitchAt(t) * Math.PI / 180);
  car.setCrush(crushAt(t)); car.setDoor(t >= T_IN - .02); car.spin((CAR0 - cx) / .34); car.setAirbag(airbagAt(t));
  // fighters
  const inCar = t >= T_IN && t < 16.18;
  gS.root.visible = gS.shadow.visible = !inCar; gC.root.visible = inCar;
  if (!inCar) gS.set(g(t));
  rv.set(r(s)); rv.root.visible = rv.shadow.visible = !(t > 4.2 && t < 16.0);
  if (inCar) {
    const p = Object.assign({}, seat(t)); p.breathe = t * 2.4; p.blink = blinkAt(t); p.mouth = p.turn > .6 ? (LOUD[Math.round(t * 60)] || 0) : 0; p.brow = p.turn > .6 ? .6 : 0;
    gC.set(p); car.group.updateMatrixWorld(true);
    const sh = car.group.worldToLocal(gC.chestPos()), hip = new THREE.Vector3(p.x, p.y, p.z);
    const lock = t >= T_CRASH && t < T_RESUME + .7 ? 1 : 0, slack = t < T_CRASH ? .05 : 0;
    const P = [car.dring.clone().add(new THREE.Vector3(0, 0, .02)), new THREE.Vector3(sh.x - .02, sh.y + .04, sh.z - .17),
      new THREE.Vector3((sh.x + hip.x) / 2 + .15 + slack, (sh.y + hip.y) / 2 + .02, sh.z - .02), new THREE.Vector3(hip.x + .1, hip.y - .02, hip.z + .2),
      new THREE.Vector3(hip.x + .16, hip.y - .04, hip.z - .05), new THREE.Vector3(hip.x + .05, hip.y - .05, -.8)];
    car.belt(P, lock && t > T_FREEZE ? 1 : 0);
  } else car.belt([car.dring.clone(), car.retr.clone()], 0);
  const c = camAt(t); st.aim(c); return { blur: c.blur };
}
function frame(i, fps) {
  const t = i / fps;
  st.frame(t, fps, pose);
  let fl = 0; for (const im of IMP) if (im.big) { const k = Math.round((t - im.t) * fps); if (k >= 0 && k < 4) fl = Math.max(fl, [.55, .3, .12, .04][k]); }
  st.post(fl);
  const ctx = st.ctx;
  if (t >= T_FREEZE && t < 5.6) { ctx.save(); ctx.globalAlpha = K.clamp((t - T_FREEZE) / .08, 0, 1) * K.clamp((5.6 - t) / .25, 0, 1) * .95; ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.roundRect(80, 330, 34, 100, 10); ctx.roundRect(136, 330, 34, 100, 10); ctx.fill(); ctx.restore(); }
  diagrams(ctx, t); limiterCard(ctx, t); headline(ctx, t); captions(ctx, t);
  if (t >= 16.92 && t < 17.62) K.poll(ctx, 160, 300, Math.min((t - 16.92) / .2, (17.62 - t) / .14), t > 17.25 ? 1 : 0);
  tag(ctx);
}
