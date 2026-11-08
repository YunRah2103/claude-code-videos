// seatbelt-fight scene (inkfight kit). Rendered by shared/assets/inkfight/render.mjs.
// 0-3 street fight | 3-4 knocked apart, dives into a parked car, launch + skid | 4.75 lamp-post crash | 5.0 freeze
// 5.2 "Quick pause." | 6.1-13.1 diagrams | 13.1-16.2 time resumes in slow motion: force limiter, airbag, he's fine
// 16.2-18 back in the street: last hit, "Did you know that?" + poll, returns to frame 1 for the loop.
(function () {
const S = {}; let ctx, wc, wx, street, post, WORDS = [], LOUD = [];
const G0 = { x: -190, y: 0, face: 1, lean: 8, head: -6, a1: 38, a2: 112, b1: 58, b2: 118, l1: 24, l2: -20, m1: -18, m2: 14, turn: 0, s: 1, sx: 1, sy: 1 };
const R0 = { x: 190, y: 0, face: -1, lean: 10, head: -4, a1: 42, a2: 108, b1: 60, b2: 114, l1: 24, l2: -20, m1: -18, m2: 14, s: 1, sx: 1, sy: 1 };
const CAR0 = -1500, CRASHX = -3600, LAMPX = CRASHX - 740 - 22, T_CRASH = 4.75, T_FREEZE = 4.95;
const SIT = { abs: 1, x: 30, y: -200, face: 1, lean: -12, head: 4, a1: 82, a2: 12, b1: 78, b2: 18, l1: 84, l2: -82, m1: 80, m2: -78, s: .9, sx: 1, sy: 1, turn: 0 };
const BLOCK = { a1: 78, a2: 128, b1: 88, b2: 122 };
const HS = 1 / 60;
// ---------- fighters ----------
const g = K.track([
  [0, G0], [.10, { x: -196, lean: 10 }],
  [.24, Object.assign({ x: -222, lean: -6, head: -10 }, BLOCK), 'o'], [.24 + 3 * HS, {}, 'l'],
  [.36, { x: -246, lean: -2 }, 'o'],
  [.42, { lean: -14, a1: 18, a2: 140, b1: 60, b2: 120, l1: 30, l2: -30 }, 'io'],
  [.50, { x: -150, lean: 24, a1: 88, a2: 4, b1: 30, b2: 120, l1: 44, l2: -10, m1: -38, m2: 6 }, 'o'],
  [.60, { lean: 6, a1: 50, a2: 100, l1: 24, l2: -20, m1: -18, m2: 14 }, 'io'],
  [.66, Object.assign({ x: -170, lean: -24, head: -22 }, BLOCK), 'o'], [.66 + 3 * HS, {}, 'l'],
  [.86, { x: -330, y: -110, lean: -16, l1: 70, l2: -110, m1: 30, m2: -100, a1: 20, a2: 90, b1: 120, b2: 40 }, 'o'],
  [1.00, { y: 0, lean: 26, head: 6, a1: 10, a2: 60, b1: -20, b2: 40, l1: 62, l2: -112, m1: -6, m2: -72 }, 'i'],
  [1.12, { x: -200, y: -250, lean: -6, l1: 98, l2: -120, m1: 14, m2: -70, a1: -30, a2: 50, b1: 130, b2: 30 }, 'o'],
  [1.31, { x: -110, y: -210, lean: -34, l1: 104, l2: -2, m1: 0, m2: -40, a1: -60, a2: 20, b1: 150, b2: 10 }, 'o'], [1.31 + 4 * HS, {}, 'l'],
  [1.55, { x: -150, y: 0, lean: 16, l1: 34, l2: -46, m1: -22, m2: 10, a1: 40, a2: 100, b1: 60, b2: 110, head: -4 }, 'io'],
  [1.72, Object.assign({}, G0, { x: -160 })],
  [1.84, Object.assign({ lean: 4 }, BLOCK), 'io'],
  [1.92, { x: -186, lean: -12, head: -14 }, 'o'], [1.92 + 3 * HS, {}, 'l'],
  [2.12, { x: -190, lean: -10, head: -4, a1: 12, a2: 145, b1: 70, b2: 115, l1: 30, l2: -30 }, 'io'],
  [2.32, { x: -205, lean: 26, a1: 92, a2: 2, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8 }, 'o'], [2.32 + 4 * HS, {}, 'l'],
  [2.52, { x: -235, lean: -4, a1: 60, a2: 110, l1: 24, l2: -20, m1: -18, m2: 14 }, 'o'],
  [2.64, Object.assign({ lean: 6, x: -230 }, BLOCK), 'io'],
  [2.75, { x: -250, lean: -30, head: -20, sx: .86, sy: 1.08 }, 'o'], [2.75 + 3 * HS, {}, 'l'],
  [3.02, { x: -720, y: -230, lean: -64, head: -10, sx: 1, sy: 1, a1: 150, a2: 20, b1: 120, b2: 40, l1: 40, l2: -30, m1: 10, m2: -50 }, 'o'],
  [3.13, { x: -900, y: -280, lean: -20, sx: .18, a1: 90, a2: 60, b1: 90, b2: 60, l1: 60, l2: -90, m1: 50, m2: -90 }, 'io'],
  [3.131, { face: -1, lean: 20 }, 'h'],
  [3.20, { x: -1020, y: -300, sx: 1, lean: 50, a1: 120, a2: 0, b1: 130, b2: 0, l1: -20, l2: 0, m1: -30, m2: 0 }, 'o'],
  [3.42, { x: -1340, y: -170, lean: 92, sx: 1.25, sy: .85, a1: 175, b1: 178, l1: -12, m1: -8 }, 'i'],
  // back in the street (16.2-18)
  [16.18, Object.assign({}, G0, { x: -980, lean: 30, a1: -20, a2: 120, b1: 100, b2: 60, l1: 60, l2: -60, m1: -40, m2: -40 })],
  [16.42, { x: -300, l1: -30, l2: -40, m1: 50, m2: -50, a1: 10, a2: 145, lean: 20 }, 'l'],
  [16.50, { x: -140, lean: 26, a1: 70, a2: 2, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8, head: -4 }, 'o'], [16.50 + 4 * HS, {}, 'l'],
  [16.66, { lean: 10, a1: 55, a2: 60 }, 'o'],
  [16.84, { x: -150, lean: 0, head: 0, turn: 1, a1: 40, a2: 90, b1: 22, b2: 40, l1: 12, l2: -6, m1: -12, m2: 6 }, 'io'],
  [17.0, { a1: 48, a2: 100 }], [17.25, { a1: 40, a2: 90 }], [17.5, {}],
  [17.66, { turn: 0 }, 'io'],
  [17.92, Object.assign({}, G0)], [18.2, Object.assign({}, G0)],
]);
const r = K.track([
  [0, R0], [.10, { x: 222, lean: -6, l1: 34, l2: -48, m1: -26, m2: -18, a1: 22, a2: 128 }, 'io'],
  [.24, { x: 26, lean: 22, a1: 92, a2: 2, b1: 52, b2: 110, l1: 46, l2: -14, m1: -40, m2: 8 }, 'o'], [.24 + 3 * HS, {}, 'l'],
  [.38, { x: 40, lean: 10, a1: 45, a2: 100 }, 'io'],
  [.48, { x: 60, lean: 52, head: 10, l1: 72, l2: -104, m1: -30, m2: -72, a1: 30, a2: 120 }, 'o'],
  [.56, { lean: 42, a1: -18, a2: 128 }, 'io'],
  [.66, { x: 10, y: -30, lean: -6, head: -8, a1: 160, a2: 24, l1: 26, l2: -10, m1: -26, m2: 6 }, 'o'], [.66 + 3 * HS, {}, 'l'],
  [.86, Object.assign({}, R0, { x: 120 }), 'io'],
  [1.18, Object.assign({ x: 110, lean: 0 }, BLOCK)],
  [1.31, { x: 128, lean: -16, head: -12 }, 'o'], [1.31 + 4 * HS, {}, 'l'],
  [1.55, { x: 240, lean: -6 }, 'o'],
  [1.70, Object.assign({}, R0, { x: 205 })],
  [1.82, { lean: -24, l1: 96, l2: -124, a1: 30, a2: 120 }, 'io'],
  [1.92, { x: 160, lean: -42, l1: 92, l2: 0, b1: -30, b2: 30 }, 'o'], [1.92 + 3 * HS, {}, 'l'],
  [2.12, Object.assign({}, R0, { x: 200 }), 'io'],
  [2.32, { x: 205, lean: 26, a1: 92, a2: 2, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8 }, 'o'], [2.32 + 4 * HS, {}, 'l'],
  [2.52, { x: 250, lean: -4, a1: 60, a2: 110, l1: 24, l2: -20, m1: -18, m2: 14 }, 'o'],
  [2.64, { x: 230, y: -60, lean: -28, l1: 102, l2: -124, m1: -10, m2: -40, a1: 20, a2: 110 }, 'io'],
  [2.75, { x: 70, y: -40, lean: -46, l1: 94, l2: 0 }, 'o'], [2.75 + 3 * HS, {}, 'l'],
  [2.98, Object.assign({}, R0, { x: 90, lean: 4 }), 'io'],
  [16.2, Object.assign({}, R0)], [16.50, { lean: -30, head: -26, x: 205, sx: .9, sy: 1.06 }, 'o'], [16.50 + 4 * HS, {}, 'l'],
  [16.76, { x: 560, y: -170, lean: -130, sx: 1, sy: 1, l1: 80, l2: -90, m1: 60, m2: -100, a1: 160, a2: 20, b1: 140, b2: 30 }, 'o'],
  [16.96, { x: 650, y: 0, lean: -18, head: 6, l1: 86, l2: -8, m1: 80, m2: -14, a1: -30, a2: 10, b1: -40, b2: 10 }, 'o'],
  [17.30, { head: -6 }], [17.44, { lean: 30, l1: 70, l2: -110, m1: -10, m2: -80, a1: 10, a2: 60, x: 640 }, 'io'],
  [17.60, { x: 420, y: -200, lean: 0, l1: 50, l2: -80, m1: 20, m2: -70, a1: 130, a2: 20, b1: 120, b2: 20 }, 'o'],
  [17.80, Object.assign({}, R0, { x: 196 }), 'io'], [17.92, Object.assign({}, R0)], [18.2, Object.assign({}, R0)],
]);
// seated guy (car-local coordinates, faces the car's front)
const sit = K.track([
  [0, SIT], [3.62, {}], [3.70, { lean: -18 }, 'o'], [4.3, { lean: -10, head: 6 }], [T_CRASH, { lean: -6 }],
  [T_CRASH + .1, { lean: 22, head: 14, a1: 96, a2: 0, b1: 90, b2: 6 }, 'o'], [T_FREEZE, { lean: 24, head: 16 }],
]);
const live = K.track([   // after the freeze (real time): turn to camera, talk, resume, airbag, shake it off
  [5.0, { lean: 24, head: 16, turn: 0, a1: 96, a2: 0, b1: 90, b2: 6 }], [5.08, {}],
  [5.28, { head: 4, turn: 1 }, 'back'], [5.9, {}],
  [6.3, { a1: 155, a2: 25, head: -4 }, 'back'], [7.1, { a1: 120, a2: 70, head: 6 }], [7.8, { a1: 150, a2: 30, head: -6 }], [8.6, { a1: 105, a2: 90, head: 4 }],
  [9.4, { a1: 158, a2: 15, head: -6 }], [10.2, { a1: 115, a2: 75, head: 6 }], [11.0, { a1: 150, a2: 30, head: -4 }], [11.9, { a1: 110, a2: 80, head: 5 }],
  [12.7, { a1: 96, a2: 0, head: 4 }], [13.12, {}],
  [13.5, { lean: 30, head: 18, turn: 0 }, 'io'],
  [13.95, { lean: 34, head: 24 }, 'o'], [14.5, { lean: 6, head: 0 }, 'io'], [14.9, { lean: -8, head: -4 }],
  [15.05, { head: 12, turn: .4 }], [15.2, { head: -10 }], [15.35, { head: 10 }], [15.5, { head: -2, turn: .2 }],
  [15.75, { turn: 1, head: 2, lean: -6, a1: 150, a2: 20 }, 'back'], [16.2, {}],
]);
// ---------- car ----------
const carX = t => { if (t < 3.5) return CAR0; if (t >= T_CRASH) return CRASHX; const u = (t - 3.5) / (T_CRASH - 3.5); return CAR0 + (CRASHX - CAR0) * Math.pow(u, 1.55); };
const crush = t => K.ease.o(K.clamp((t - T_CRASH - 4 * HS) / .1, 0, 1));
const pitch = t => t < 3.5 ? 0 : t < 3.75 ? -2.5 * Math.sin((t - 3.5) / .25 * Math.PI) : t < 4.32 ? 0 : t < T_CRASH ? 2.2 * K.sm((t - 4.32) / .15) : 2.2 * Math.exp(-(t - T_CRASH) * 12) * Math.cos((t - T_CRASH) * 40);
const simT = t => t < T_FREEZE ? t : T_FREEZE;  // world clock (frozen after the crash)
// ---------- impacts (time, world pos, shake px, flash, frame-invert) ----------
const IMP = [
  { t: .24, p: [-150, -500], sh: 14, fl: .45, s: 'block' },
  { t: .66, p: [-120, -560], sh: 18, fl: .55, s: 'punch' },
  { t: 1.31, p: [30, -520], sh: 28, fl: .85, inv: 1, s: 'punch_big' },
  { t: 1.92, p: [-120, -430], sh: 18, fl: .5, s: 'punch' },
  { t: 2.32, p: [0, -500], sh: 36, fl: 1, inv: 1, s: 'clash' },
  { t: 2.75, p: [-170, -440], sh: 26, fl: .7, s: 'punch_big' },
  { t: T_CRASH, p: [LAMPX + 30, -270], sh: 46, fl: 1, inv: 1, s: 'crash' },
  { t: 16.5, p: [150, -560], sh: 34, fl: 1, inv: 1, s: 'punch_big' },
];
const WHOOSH = [.15, .44, 1.08, 1.84, 2.26, 2.66, 2.86, 3.30, 16.22, 16.42, 17.5];
// ---------- camera ----------
const occW = (lx, ly, t) => [carX(t) - lx, ly];        // car-local -> world (car faces left)
const HEADL = [-30, -470];
const shots = [
  { t0: 0, t1: .38, a: { x: 0, y: -380, z: 1.32 }, b: { x: -24, y: -390, z: 1.4 } },
  { t0: .38, t1: .95, a: { x: -70, y: -430, z: 1.95, r: .035 }, b: { x: -60, y: -440, z: 2.1, r: .03 } },
  { t0: .95, t1: 1.70, a: { x: -110, y: -450, z: 1.05 }, b: { x: -40, y: -430, z: 1.14 } },
  { t0: 1.70, t1: 2.26, a: { x: -10, y: -440, z: 1.5, r: -.02 }, b: { x: 0, y: -440, z: 1.62, r: -.02 } },
  { t0: 2.26, t1: 2.50, a: { x: 0, y: -500, z: 3.1 }, b: { x: 0, y: -500, z: 3.4 } },
  { t0: 2.50, t1: 2.80, a: { x: -80, y: -420, z: 1.45 }, b: { x: -150, y: -420, z: 1.35 } },
  { t0: 2.80, t1: 3.42, a: { x: -200, y: -430, z: 1.3 }, b: { x: -1260, y: -470, z: 1.05 }, e: 'i' },
  { t0: 3.42, t1: 3.80, rel: 1, a: { x: -60, y: -420, z: 2.3 }, b: { x: -40, y: -400, z: 1.9 }, e: 'o' },
  { t0: 3.80, t1: T_CRASH, rel: 1, a: { x: -40, y: -400, z: 1.9 }, b: { x: -900, y: -440, z: .55 }, e: 'io' },
  { t0: T_CRASH + 4 * HS, t1: 4.95, rel: 1, a: { x: -20, y: -400, z: 2.2 }, b: { x: -40, y: -390, z: 2.35 }, e: 'o' },
  { t0: 4.95, t1: 5.32, rel: 1, a: { x: -40, y: -390, z: 2.35 }, b: { x: -30, y: -380, z: 3.0 }, e: 'io' },
  { t0: 5.32, t1: 5.9, rel: 1, a: { x: -30, y: -380, z: 3.0 }, b: { x: -20, y: -640, z: 1.9 }, e: 'io' },
  { t0: 5.9, t1: 13.12, rel: 1, a: { x: -20, y: -640, z: 1.9 }, b: { x: -10, y: -650, z: 2.0 }, e: 'l' },
  { t0: 13.12, t1: 16.2, rel: 1, a: { x: -10, y: -650, z: 2.0 }, b: { x: -10, y: -600, z: 2.15 }, e: 'io' },
  { t0: 16.2, t1: 16.42, a: { x: CRASHX - 10, y: -560, z: 2.0 }, b: { x: -200, y: -430, z: 1.3 }, e: 'io' },
  { t0: 16.42, t1: 16.62, a: { x: -20, y: -460, z: 1.5 }, b: { x: 0, y: -460, z: 1.6 } },
  { t0: 16.62, t1: 17.6, a: { x: -60, y: -440, z: 1.35 }, b: { x: -80, y: -450, z: 1.45 }, e: 'io' },
  { t0: 17.6, t1: 17.92, a: { x: -80, y: -450, z: 1.45 }, b: { x: 0, y: -380, z: 1.32 }, e: 'io' },
  { t0: 17.92, t1: 18.1, a: { x: 0, y: -380, z: 1.32 } },
];
const camRaw = K.camera(shots, IMP.map(i => ({ t: i.t, shake: i.sh })));
const cam = t => { const c = camRaw(t); if (c.shot.rel) { c.x += carX(simT(t)) - CRASHX + CRASHX; } return c; };
// rel shots: x is relative to the car centre
const camAt = t => { const c = camRaw(t); if (c.shot.rel) c.x += carX(simT(t)); return c; };
// ---------- drawing ----------
function fighters(c, t) {
  const drawOne = (trk, isG) => {
    const p = ground(trk(t));
    if (isG && t >= 3.42 && t < 16.18) return;
    const J = K.joints(p);
    // smears for fast hands/feet
    for (const key of ['ha', 'hb', 'fa', 'fb']) {
      const pts = []; for (let k = 0; k < 6; k++) pts.push(K.joints(ground(trk(t - k / 60)))[key]);
      K.smear(c, pts, 34, isG ? 'rgba(255,240,220,.9)' : 'rgba(255,90,70,.9)');
    }
    K.shadow(c, J.hip[0], 120, .5 * K.clamp(1 + p.y / 300, 0, 1));
    if (isG) K.drawGuy(c, p, { mouth: 0, blink: blinkAt(t) }); else K.drawRival(c, p, { t });
  };
  drawOne(r, false); drawOne(g, true);
}
function ground(p) { if (p.abs) return p; const q = Object.assign({}, p, { y: 0 }); const J = K.joints(q); const low = Math.max(J.fa[1], J.fb[1]); return Object.assign(p, { y: -low - 9 + p.y }); }
const blinkAt = t => ((t * 1000) % 2900) < 110;
function occupant(c, t) {   // drawn in car-local coords (x forward)
  const st = simT(t);
  let p = Object.assign({}, sit(st));
  if (t >= 5.0) p = Object.assign(p, live(t));
  const pay = t < 13.12 ? 0 : K.sm((t - 13.2) / .6) * 16;     // force limiter: belt pays out a little
  // seat
  c.fillStyle = '#2c3760'; c.beginPath(); c.roundRect(-150, -235, 260, 70, 26); c.fill();
  c.save(); c.translate(-110, -210); c.rotate(-.2); c.fillStyle = '#3c4a78'; c.beginPath(); c.roundRect(-40, -300, 80, 320, 34); c.fill(); c.beginPath(); c.roundRect(-34, -375, 66, 80, 22); c.fill(); c.restore();
  // pillar + retractor
  c.fillStyle = '#4a4f66'; c.fillRect(-196, -480, 28, 360);
  c.fillStyle = '#7f8696'; c.beginPath(); c.roundRect(-214, -170, 60, 60, 12); c.fill();
  // wheel + airbag
  const bag = t < 13.62 ? 0 : t < 14.55 ? (t - 13.62) / .22 : Math.max(0, 1 - (t - 14.55) / .5) * .999 + .001;
  c.strokeStyle = '#1c1f2c'; c.lineWidth = 16; c.lineCap = 'round'; c.beginPath(); c.moveTo(250, -390); c.lineTo(205, -270); c.stroke();
  c.beginPath(); c.moveTo(232, -330); c.lineTo(300, -300); c.stroke();
  const J = K.joints(p);
  K.drawGuy(c, p, { mouth: p.turn > .5 ? mouthAt(t) : 0, blink: blinkAt(t), thumb: t > 15.75, brow: t > 5.2 && t < 13 ? .6 : 0 });
  if (bag > 0) K.airbag(c, 228, -340, bag, 1);
  // belt: D-ring -> shoulder -> across chest -> buckle, lap belt
  const locked = t >= T_CRASH && t < 13.6 ? 1 : 0, slack = t < T_CRASH ? .3 : 0;
  const sh = [J.chest[0] + 6, J.chest[1] + 16], hp = [J.hip[0] + 34, J.hip[1] + 6];
  c.save(); if (locked && t > 4.95) { c.shadowColor = '#ffb347'; c.shadowBlur = 30; }
  c.strokeStyle = '#ffb347'; c.lineWidth = 17; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath(); c.moveTo(-182, -440 - pay); c.lineTo(sh[0], sh[1]);
  const mx = (sh[0] + hp[0]) / 2 + 26 + slack * 40, my = (sh[1] + hp[1]) / 2;
  c.quadraticCurveTo(mx, my, hp[0], hp[1]); c.lineTo(-120, -205); c.stroke();
  c.beginPath(); c.moveTo(-182, -440 - pay); c.lineTo(-182, -150); c.stroke();
  c.restore();
  c.fillStyle = '#c9ced8'; c.beginPath(); c.roundRect(-196, -456 - pay, 30, 26, 6); c.fill();
  c.fillStyle = '#c9ced8'; c.beginPath(); c.roundRect(hp[0] - 12, hp[1] - 14, 30, 22, 6); c.fill();
}
const mouthAt = t => { const i = Math.round(t * 60); return LOUD[i] || 0; };
function lampPost(c, t) {
  const st = simT(t), bend = st < T_CRASH ? 0 : -16 * K.ease.back(K.clamp((st - T_CRASH) / .12, 0, 1));
  c.save(); c.translate(LAMPX, 0); c.fillStyle = '#4a4e78'; c.fillRect(-14, -330, 28, 334); c.fillStyle = 'rgba(255,190,110,.7)'; c.fillRect(6, -330, 8, 334); c.fillStyle = '#4a4e78';
  c.translate(0, -330); c.rotate(bend * Math.PI / 180); c.fillRect(-12, -900, 24, 905); c.fillRect(-12, -900, 150, 18);
  const gg = c.createRadialGradient(130, -878, 4, 130, -878, 200); gg.addColorStop(0, 'rgba(255,220,160,1)'); gg.addColorStop(.2, 'rgba(255,170,90,.45)'); gg.addColorStop(1, 'rgba(255,170,90,0)');
  c.fillStyle = gg; c.fillRect(-80, -1090, 420, 420); c.fillStyle = '#fff1cf'; c.beginPath(); c.ellipse(130, -872, 40, 12, 0, 0, 7); c.fill();
  c.restore();
  // barrier stripes at the base
  c.fillStyle = '#ffd35f'; c.fillRect(LAMPX - 60, -70, 120, 70); c.fillStyle = '#1a1a24'; for (let i = 0; i < 4; i++) c.fillRect(LAMPX - 60 + i * 34, -70, 14, 70);
}
function world(c, t, cm) {
  const st = simT(t);
  K.drawStreet(c, street, cm, st);
  lampPost(c, t);
  // tyre smoke + skid marks behind the car
  const cx = carX(st);
  if (st > 3.5 && st < T_CRASH + .6) {
    c.fillStyle = 'rgba(10,10,16,.55)'; c.fillRect(Math.min(cx + 450, CAR0 + 500), 6, Math.max(0, CAR0 + 500 - cx - 450), 9);
    for (let k = 0; k < 14; k++) { const tt = st - k * .04; if (tt < 3.5) break; const x = carX(tt) + 420 + k * 30, a = (1 - k / 14) * (st > 4.32 || st < 3.8 ? .5 : .2);
      c.fillStyle = `rgba(200,205,220,${a})`; c.beginPath(); c.arc(x, -60 - k * 6, 40 + k * 7, 0, 7); c.fill(); }
  }
  const showOcc = t >= 3.42 && t < 16.18;
  K.drawCar(c, cx, -1, { crush: crush(st), pitch: pitch(st), spin: (CAR0 - cx) / K.CAR.wheel * (st < 3.75 && st > 3.5 ? 1.6 : 1), doorOff: showOcc && t >= T_CRASH + 4 * HS, glass: showOcc ? .1 : .3,
    col: '#2a9fb4', col2: '#7fe0ea', occupant: showOcc ? (cc => occupant(cc, t)) : null });
  // ghost door outline in the cutaway
  if (showOcc && t >= T_CRASH + 4 * HS) { c.save(); c.translate(cx, 0); c.scale(-1, 1); c.strokeStyle = 'rgba(255,207,106,.5)'; c.setLineDash([16, 12]); c.lineWidth = 5; c.strokeRect(-340, -395, 640, 225); c.restore(); }
  if (t < 16.18 || t >= 16.18) fighters(c, t);
  // FX
  IMP.forEach((im, k) => { const a = st - im.t; if (t >= 16.18 && im.t < 16) return;
    K.burst(c, im.p[0], im.p[1], a, im.s === 'crash' ? 260 : 170, 11 + k);
    K.sparks(c, im.p[0], im.p[1], a, im.s === 'crash' ? 40 : 18, 31 + k, im.s === 'crash' ? 1300 : 800);
    if (im.s === 'crash') { K.dust(c, im.p[0] + 120, -40, a, 16, 5, 90, 1); glass(c, im.p, a); }
  });
  [1.55, 1.0, 16.96].forEach((tt, k) => K.dust(c, k === 2 ? 650 : k ? -330 : 230, -10, st - tt, 8, 70 + k, 50));
}
function glass(c, p, a) { if (a < 0 || a > 1) return; const rr = K.rng(5); c.save();
  for (let i = 0; i < 16; i++) { const vx = 300 + rr() * 700, vy = -500 - rr() * 500, x = p[0] + 160 + vx * a, y = p[1] - 150 + vy * a + 1400 * a * a;
    c.globalAlpha = 1 - a; c.fillStyle = i % 2 ? 'rgba(170,230,255,.9)' : 'rgba(255,255,255,.9)'; c.save(); c.translate(x, y); c.rotate(a * 12 + i);
    c.beginPath(); c.moveTo(0, -12); c.lineTo(10, 8); c.lineTo(-9, 6); c.fill(); c.restore(); }
  c.restore(); }
// ---------- overlays: diagrams, headline, captions ----------
const wordAt = w => (WORDS.find(x => x.w.toLowerCase().replace(/[^a-z']/g, '') === w) || {}).s;
let CH = [];
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
  const H = [[S.T.v1, S.T.v2, 'MEET THE PRETENSIONER'], [S.T.v2, S.T.v3, 'IT FIRES IN A CRASH'], [S.T.v3, S.T.v4, 'WHY SNUG MATTERS'], [S.T.v4, 16.2, 'THE FORCE LIMITER']];
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
  const rr = K.rng(3); c.globalCompositeOperation = 'screen'; t *= 2.6;      // slow drifting bokeh keeps the panel alive
  for (let i = 0; i < 22; i++) { const sp = 60 + rr() * 140, x = (rr() * 1300 + t * sp * (rr() < .5 ? .5 : -.5)) % 1300 - 110, y = 1150 - ((rr() * 1000 + t * sp) % 1000), R = 30 + rr() * 80;
    const col = rr() < .5 ? '95,227,255' : '255,179,71', gg = c.createRadialGradient(x, y, 0, x, y, R); gg.addColorStop(0, `rgba(${col},${.4 * a})`); gg.addColorStop(1, `rgba(${col},0)`);
    c.fillStyle = gg; c.fillRect(x - R, y - R, 2 * R, 2 * R); }
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
  const a = K.clamp((t - S.T.v4) / .3, 0, 1) * K.clamp((16.1 - t) / .3, 0, 1); if (a <= 0) return;
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = a; c.translate(0, (1 - K.ease.o(a)) * 30);
  c.fillStyle = 'rgba(10,14,32,.88)'; c.beginPath(); c.roundRect(70, 400, 820, 420, 34); c.fill();
  const pay = K.sm((t - 13.2) / .6), load = t < 13.25 ? .55 : t < 13.6 ? .55 + (t - 13.25) / .35 * .4 : .95 - K.sm((t - 13.6) / .5) * .45;
  c.strokeStyle = K.DG.belt; c.lineWidth = 30; c.beginPath(); c.moveTo(330, 440); c.lineTo(330, 610); c.stroke();
  K.spool(c, 250, 640, 80, pay * 2.2 + (t - 13.12) * .2, .9 - pay * .15);
  if (t > 13.25 && t < 15.2) K.arrow(c, 400, 640, 400, 470, '#5fe3ff', 9);
  c.fillStyle = '#20263d'; c.beginPath(); c.roundRect(600, 450, 70, 300, 20); c.fill();
  const col = load > .8 ? '#ff4a3d' : '#7dffb0'; c.fillStyle = col; c.beginPath(); c.roundRect(610, 460 + 280 * (1 - load), 50, 280 * load, 14); c.fill();
  c.strokeStyle = 'rgba(255,255,255,.7)'; c.lineWidth = 4; c.setLineDash([10, 8]); c.beginPath(); c.moveTo(585, 460 + 280 * .1); c.lineTo(690, 460 + 280 * .1); c.stroke();
  c.restore();
  if (a > .5) { K.text(c, 'Belt pays out', 110, 750, { size: 38, weight: 800, color: '#5fe3ff' }); K.text(c, 'Chest load', 560, 760, { size: 38, weight: 800, color: col }); }
}
function pauseIcon(c, t) {
  if (t < 4.97 || t > 5.9) return; const a = K.clamp((t - 4.97) / .08, 0, 1) * K.clamp((5.9 - t) / .2, 0, 1);
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = a * .95; c.fillStyle = '#fff';
  c.beginPath(); c.roundRect(80, 330, 34, 100, 10); c.roundRect(136, 330, 34, 100, 10); c.fill();
  c.strokeStyle = 'rgba(255,255,255,.35)'; c.lineWidth = 3; for (let i = 0; i < 5; i++) { const y = (i * 397 + t * 2100) % 1920; c.beginPath(); c.moveTo(0, y); c.lineTo(1080, y + 6); c.stroke(); }
  c.restore();
}
// ---------- frame ----------
S.init = d => {
  const cv = document.getElementById('c'); ctx = cv.getContext('2d');
  wc = document.createElement('canvas'); wc.width = K.W; wc.height = K.H; wx = wc.getContext('2d');
  street = K.buildStreet(-6200, 1800); post = K.makePost();
  WORDS = d.words; LOUD = d.loud; CH = chunks();
  S.T = { v1: wordAt('your'), tighten: wordAt('tighten'), v2: wordAt('in'), crashW: wordAt('crash'), charge: wordAt('charge'), motor: wordAt('motor'), v3: wordAt('snug') - .3, v4: wordAt('then') };
  S.events = { impacts: IMP.map(i => ({ t: i.t, s: i.s })), whoosh: WHOOSH, crash: T_CRASH, freeze: 4.97, airbag: 13.62, click: 3.5,
    screech: [3.52, 4.3], land: [1.0, 1.55, 16.96], scratch: 4.97, T: S.T };
};
S.frame = (f, fps) => {
  const t = f / fps, cm = camAt(t), cp = camAt(t - 1 / fps);
  wx.setTransform(1, 0, 0, 1, 0, 0); wx.fillStyle = '#0d1424'; wx.fillRect(0, 0, K.W, K.H);
  wx.save(); K.apply(wx, cm); world(wx, t, cm); wx.restore();
  // composite with motion blur along fast camera moves
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.filter = 'none';
  const vx = (cm.x - cp.x) * cm.z, vy = (cm.y - cp.y) * cm.z, sp = Math.hypot(vx, vy), cut = cm.shot !== cp.shot;
  const frozen = t >= 4.97 && t < 13.12, sat = frozen ? (t < 5.1 ? .25 : .55) : 1;
  ctx.filter = sat < 1 ? `saturate(${sat}) brightness(.92)` : 'none';
  if (!cut && sp > 30) { const n = 8, L = Math.min(sp, 260); ctx.globalAlpha = 1; ctx.drawImage(wc, 0, 0); for (let k = 1; k < n; k++) { ctx.globalAlpha = .45 / k * 1.6 > 1 ? 1 : .5; ctx.drawImage(wc, -vx / sp * L * k / n, -vy / sp * L * k / n); } ctx.globalAlpha = 1; }
  else ctx.drawImage(wc, 0, 0);
  ctx.filter = 'none';
  // impact frames: one inverted high-contrast frame, then white flash decay
  for (const im of IMP) { const k = Math.round((t - im.t) * fps);
    if (k === 0 && im.inv) { ctx.filter = 'grayscale(1) invert(1) contrast(3)'; ctx.drawImage(ctx.canvas, 0, 0); ctx.filter = 'none'; }
    const fl = k === 0 ? (im.inv ? .25 : .75) : k === 1 ? .55 : k === 2 ? .25 : k === 3 ? .1 : 0;
    if (fl > 0 && k >= 0) { ctx.fillStyle = `rgba(255,248,232,${fl * im.fl})`; ctx.fillRect(0, 0, K.W, K.H); } }
  if (frozen) { ctx.fillStyle = 'rgba(40,90,140,.12)'; ctx.fillRect(0, 0, K.W, K.H); }
  post(ctx, f, { bloom: frozen ? .2 : .34 });
  // overlays (sharp, after post)
  pauseIcon(ctx, t); diagrams(ctx, t); limiterCard(ctx, t); headline(ctx, t); captions(ctx, t);
  if (t >= 16.92 && t < 17.8) K.poll(ctx, 160, 300, Math.min((t - 16.92) / .2, (17.8 - t) / .14), t > 17.25 ? 1 : 0);
  tag(ctx);
};
window.SCENE = S;
})();
