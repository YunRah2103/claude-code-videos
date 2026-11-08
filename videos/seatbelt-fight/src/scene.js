// seatbelt-fight v4 (2D): solid flat fighters on a 6-layer parallax dusk street, drawn at 2x and downsampled.
// 0-3 fight (wide + big close-ups, one full-frame flash on the finishing back kick) | 2.78-3.55 knocked flying, whip pan,
// dives into the parked car | 3.6-4.0 seated, buckles up | 4.0 launch | 5.0 hits the barrier: flash, freeze, record scratch,
// push in to the locked belt | 5.25 "Quick pause." | 6.1-13.1 explainer (he keeps gesturing, slow push-in)
// 13.1 time resumes: force limiter, airbag, he's fine | 16.2 whip pan back to the street | 16.55 last hit | 16.9 question + poll | 18 = frame 1.
(function () {
const S = {}; let ctx, wc, wx, L, WORDS = [], LOUD = [];
const HS = 1 / 60, SS = 2;                       // supersampling factor
const hold = (t, n) => [t + n * HS, {}, 'l'];
const T_IN = 3.6, T_GO = 4.0, T_CRASH = 5.0, T_FREEZE = 5.05, T_RESUME = 13.1, T_BACK = 16.2;
const CAR0 = -2350, BARX = -7600, CRASHX = BARX + 70 + 740;
const G0 = { x: -250, y: 0, face: 1, lean: 8, head: -4, a1: 35, a2: 115, b1: 55, b2: 120, l1: 22, l2: -18, m1: -20, m2: 12, turn: 0, rot: 0, yaw: 0, sx: 1, sy: 1, ya: 0 };
const R0 = Object.assign({}, G0, { x: 250, face: -1, lean: 10, a1: 40, a2: 110, b1: 58, b2: 116 });
const BLOCK = { a1: 75, a2: 128, b1: 85, b2: 122 };
const CROUCH = { l1: 62, l2: -110, m1: -8, m2: -74 };
// ---------- fighters: hand-keyed (anticipation slower than the strike; hit-stops are held keys) ----------
const g = K.track([
  [0, G0],
  [.25, { x: -232, lean: 12, l1: 30, l2: -24 }, 'io'],                                                   // weight onto the front foot
  [.38, { x: -244, lean: -2, head: -8, l1: 22, l2: -18 }, 'io'],
  [.46, { lean: -16, head: -18, a1: 62, a2: 122, b1: 72, b2: 120 }, 'o'],                                // slips the jab
  [.62, Object.assign({}, G0, { x: -236, lean: 4 }), 'io'], [.70, { lean: 8 }, 'io'],                    // overshoot + settle
  [.80, { lean: 0, a1: 20, a2: 132, l1: 26, l2: -26 }, 'io'],                                             // cocks the jab
  [.86, { x: -150, lean: 24, a1: 88, a2: 6, l1: 40, l2: -10, m1: -36, m2: 6 }, 'o'], hold(.86, 2),       // jab (blocked)
  [1.0, Object.assign({}, G0, { x: -170, lean: 6 }), 'io'],
  [1.28, { x: -180, lean: -22, l1: 96, l2: -126, m1: -14, m2: 6, a1: 62, a2: 104, b1: -18, b2: 60 }, 'io'], // slow chamber
  [1.40, { x: -120, lean: -30, l1: 98, l2: -2, m1: -6, m2: -8, a1: -38, a2: 30, b1: 118, b2: 22 }, 'o'], hold(1.40, 3), // roundhouse
  [1.58, { l1: 62, l2: -104, lean: -4, a1: 40, a2: 110, b1: 55, b2: 120 }, 'io'],
  [1.74, Object.assign({}, G0, { x: -130, lean: 12 }), 'io'], [1.84, { lean: 8 }, 'io'],
  [1.97, { x: -120, lean: 14 }],
  [2.07, Object.assign({ x: -110, lean: 38, head: 12, a1: 30, a2: 130, b1: 40, b2: 120 }, CROUCH), 'o'],  // ducks the hook
  [2.18, { lean: 30, a1: 10, a2: 140 }, 'io'],
  [2.28, { y: -14, lean: 2, head: -6, a1: 166, a2: 18, l1: 26, l2: -10, m1: -24, m2: 6 }, 'o'], hold(2.28, 2), // uppercut (blocked)
  [2.44, Object.assign({}, G0, { x: -112, lean: 4 }), 'io'], [2.52, { lean: 8 }, 'io'],
  [2.66, Object.assign({ x: -116, lean: 4 }, BLOCK), 'io'],
  [2.78, { x: -128, lean: -34, head: -20, sx: .92, sy: 1.05 }, 'o'], hold(2.78, 3),                       // takes the back kick
  [2.78 + 3 * HS + .001, { ya: 272 }, 'h'],
  [3.04, { x: -760, ya: 470, sx: 1, sy: 1, lean: -55, head: -12, l1: 34, l2: -40, m1: 10, m2: -60, a1: 150, a2: 30, b1: 125, b2: 40 }, 'o'],
  [3.16, { x: -1120, ya: 520, lean: -20, l1: 70, l2: -110, m1: 60, m2: -110, a1: 90, a2: 70, b1: 90, b2: 70 }, 'io'],
  [3.28, { x: -1520, ya: 530, yaw: 180, lean: 60, head: -10, a1: 165, a2: 5, b1: 160, b2: 5, l1: -20, l2: -10, m1: -12, m2: -20 }, 'io'], // turns to dive
  [3.56, { x: -2330, ya: 430, lean: 86, head: -14, sx: 1.08, sy: .94 }, 'i'],
  [T_IN, { ya: 0 }, 'h'],
  [16.16, Object.assign({}, G0, { x: -760, lean: 28, a1: -10, a2: 130, b1: 90, b2: 70, l1: 60, l2: -40, m1: -50, m2: -50 })],
  [16.42, { x: -240, l1: -30, l2: -40, m1: 50, m2: -50, a1: 12, a2: 140, lean: 20 }, 'l'],
  [16.55, { x: -40, lean: 26, a1: 82, a2: 4, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8, head: -4 }, 'o'], hold(16.55, 3),
  [16.72, { lean: 10, a1: 55, a2: 60 }, 'io'],
  [16.95, { x: -150, lean: 0, head: 0, turn: 1, a1: 30, a2: 70, b1: 22, b2: 40, l1: 12, l2: -6, m1: -12, m2: 6 }, 'io'],
  [17.2, { a1: 60, a2: 100 }], [17.5, {}],
  [17.62, { turn: 0 }, 'io'], [17.93, Object.assign({}, G0)], [18.2, Object.assign({}, G0)],
]);
const r = K.track([
  [0, R0],
  [.25, { x: 236, lean: 4 }, 'io'],
  [.38, { x: 240, lean: 0, a1: 20, a2: 132, l1: 26, l2: -26 }, 'io'],                                     // winds the jab
  [.46, { x: 120, lean: 24, a1: 88, a2: 4, l1: 40, l2: -10, m1: -36, m2: 6 }, 'o'],
  [.64, Object.assign({}, R0, { x: 200, lean: 6 }), 'io'], [.74, { lean: 10 }, 'io'],
  [.86, Object.assign({ x: 210, lean: -6 }, BLOCK), 'o'], hold(.86, 2),
  [1.05, Object.assign({}, R0, { x: 214 }), 'io'],
  [1.30, Object.assign({ x: 216, lean: 0 }, BLOCK), 'io'],
  [1.40, { x: 226, lean: -18, head: -16, sx: .95 }, 'o'], hold(1.40, 3),                                 // eats the roundhouse
  [1.62, { x: 300, lean: -8, head: -4, sx: 1, l1: 40, l2: -30, m1: -34, m2: 6 }, 'o'],                   // steps back (legs open, no slide)
  [1.80, Object.assign({}, R0, { x: 300 }), 'io'],
  [1.97, { x: 250, lean: 4, a1: 30, a2: 124 }, 'io'],                                                     // loads the hook
  [2.08, { x: 130, lean: 28, a1: 98, a2: 80 }, 'o'],
  [2.22, { lean: 8, a1: 42, a2: 108 }, 'io'],
  [2.28, Object.assign({ x: 135, lean: -10, head: -8 }, BLOCK), 'o'], hold(2.28, 2),
  [2.44, Object.assign({}, R0, { x: 150 }), 'io'],
  [2.56, { x: 152, lean: 6, yaw: 70, l1: 40, l2: -60 }, 'i'],                                             // spins
  [2.68, { yaw: 180, lean: 26, l1: -60, l2: -110, a1: 20, a2: 90, b1: 30, b2: 90 }, 'l'],
  [2.78, { x: 140, yaw: 182, lean: 42, l1: -98, l2: -2, m1: 14, m2: -14 }, 'o'], hold(2.78, 3),           // back kick
  [3.0, { yaw: 300, lean: 10, l1: 30, l2: -40, m1: -18, m2: 12, x: 160 }, 'io'],
  [3.16, Object.assign({}, R0, { x: 170, yaw: 360 }), 'io'], [3.161, { yaw: 0 }, 'h'],
  [T_RESUME, {}], [16.3, Object.assign({}, R0, { x: 210 })],
  [16.55, { lean: -32, head: -26, sx: .94, x: 225 }, 'o'], hold(16.55, 3),
  [16.85, { x: 640, y: -130, rot: -40, lean: -30, sx: 1, l1: 60, l2: -80, m1: 40, m2: -60, a1: 160, a2: 20, b1: 140, b2: 30 }, 'o'],
  [17.1, { x: 760, y: 0, rot: 0, lean: -18, head: 6, l1: 86, l2: -8, m1: 80, m2: -14, a1: -30, a2: 10, b1: -40, b2: 10 }, 'o'],
  [17.35, Object.assign({ x: 740, lean: 30, a1: 10, a2: 60 }, CROUCH), 'io'],
  [17.6, { x: 480, y: -170, lean: 0, l1: 50, l2: -80, m1: 20, m2: -70, a1: 130, a2: 20, b1: 120, b2: 20 }, 'o'],
  [17.82, Object.assign({}, R0, { x: 262 }), 'io'], [17.93, Object.assign({}, R0)], [18.2, Object.assign({}, R0)],
]);
// him in the car (car-local coords, faces the car's front)
const SIT = { abs: 1, x: 30, y: -200, face: 1, lean: -12, head: 4, a1: 82, a2: 12, b1: 78, b2: 18, l1: 84, l2: -82, m1: 80, m2: -78, s: .9, sx: 1, sy: 1, turn: 0 };
const seat = K.track([
  [T_IN, Object.assign({}, SIT, { y: -250, lean: 30, sy: .88 })], [T_IN + .16, SIT, 'o'],
  [3.74, { a1: 150, a2: 60, head: -10 }, 'io'], [3.86, { a1: 60, a2: 40, head: 4 }, 'o'], [3.96, { a1: 82, a2: 12 }],    // pulls the belt across, click
  [T_GO, {}], [T_GO + .12, { lean: -20, head: 8 }, 'o'], [4.7, { lean: -16, head: 4 }],
  [T_CRASH, {}], [T_FREEZE, { lean: 22, head: 16, a1: 96, a2: 0, b1: 90, b2: 6 }, 'o'],
  [5.12, {}], [5.36, { turn: 1, head: 0, lean: 6 }, 'back'],
  [6.1, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [6.55, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [6.95, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [7.35, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [7.75, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [8.15, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [8.55, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [8.95, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [9.35, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [9.75, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [10.15, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [10.55, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [10.95, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [11.35, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [11.75, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [12.15, { a1: 118, a2: 22, head: -6, lean: -5 }, 'o'],
  [12.6, { a1: 38, a2: 95, head: 5, lean: 4 }, 'io'],
  [12.9, { a1: 82, a2: 12, head: 2, lean: 0 }],
  [T_RESUME, { lean: -4, turn: 1 }],
  [13.45, { lean: 26, head: 18, turn: .1 }, 'io'], [13.75, { lean: 32, head: 22 }, 'o'],
  [14.4, { lean: -8, head: 0 }, 'io'], [14.9, { turn: .5, head: 12 }], [15.1, { head: -10 }], [15.3, { head: 10 }], [15.5, { head: 0, turn: 1 }],
  [15.75, { a1: 150, a2: 30 }, 'back'], [16.2, {}],
]);
// ---------- car ----------
const carX = t => t < T_GO ? CAR0 : t < T_CRASH ? CAR0 - (CAR0 - CRASHX) * Math.pow((t - T_GO) / (T_CRASH - T_GO), 1.7) : CRASHX;
const simT = t => t >= T_FREEZE && t < T_RESUME ? T_FREEZE : t;
const crushAt = t => K.ease.o(K.clamp((simT(t) - T_CRASH) / .06, 0, 1));
const pitchAt = t => { const s = simT(t); if (s < T_GO) return 0; if (s < T_CRASH) return -2.2 * Math.sin(Math.min(1, (s - T_GO) / .35) * Math.PI);
  if (s < T_RESUME) return 3 * K.ease.o(K.clamp((s - T_CRASH) / .05, 0, 1)); return 3 * Math.exp(-(s - T_RESUME) * 3) * Math.cos((s - T_RESUME) * 9); };
const airbagAt = t => t < 13.42 ? 0 : t < 13.62 ? (t - 13.42) / .2 : t < 14.6 ? 1 : Math.max(.001, 1 - (t - 14.6) / .55);
// ---------- impacts ----------
const IMP = [
  { t: .86, p: [-10, -480], k: 'small', s: 'block' }, { t: 1.40, p: [120, -520], k: 'mid', s: 'punch_big' },
  { t: 2.28, p: [40, -560], k: 'small', s: 'block' }, { t: 2.78, p: [-60, -430], k: 'big', s: 'punch_big' },
  { t: T_CRASH, p: [BARX + 60, -260], k: 'big', s: 'crash' }, { t: 16.55, p: [170, -560], k: 'big', s: 'punch_big' },
];
const STRIKES = [.46, .86, 1.40, 2.08, 2.28, 2.78, 3.0, 3.3, 16.55];
const WHOOSH = [.42, .84, 1.36, 2.05, 2.26, 2.62, 2.74, 3.1, 16.24, 16.5];
// ---------- camera (shot lengths ~0.5-0.7 s in the fight, like the reference) ----------
const shots = [
  { t0: 0, t1: .62, a: { x: 0, y: -330, z: 1.3 }, b: { x: -10, y: -340, z: 1.36 } },
  { t0: .62, t1: 1.22, a: { x: -90, y: -450, z: 2.2 }, b: { x: -70, y: -450, z: 2.32 } },
  { t0: 1.22, t1: 1.80, a: { x: 0, y: -360, z: 1.45, r: .02 }, b: { x: 30, y: -360, z: 1.5, r: .02 } },
  { t0: 1.80, t1: 2.36, a: { x: 10, y: -420, z: 2.0 }, b: { x: 20, y: -430, z: 2.12 } },
  { t0: 2.36, t1: 2.84, a: { x: 0, y: -340, z: 1.32 }, b: { x: -30, y: -340, z: 1.38 } },
  { t0: 2.84, t1: 3.56, relG: 1, a: { x: 90, y: -400, z: 1.35 }, b: { x: 80, y: -470, z: 1.3 }, e: 'io' },
  { t0: 3.56, t1: T_GO, rel: 1, a: { x: 120, y: -420, z: 2.0 }, b: { x: 110, y: -410, z: 1.9 }, e: 'o' },
  { t0: T_GO, t1: T_CRASH, rel: 1, a: { x: 110, y: -410, z: 1.9 }, b: { x: -420, y: -380, z: .74 }, e: 'io' },
  { t0: T_CRASH, t1: T_FREEZE, rel: 1, a: { x: -420, y: -380, z: .74 } },
  { t0: T_FREEZE, t1: 5.34, rel: 1, a: { x: -420, y: -380, z: .74 }, b: { x: 20, y: -380, z: 2.9 }, e: 'io' },
  { t0: 5.34, t1: 5.95, rel: 1, a: { x: 20, y: -380, z: 2.9 }, b: { x: 170, y: -600, z: 1.8 }, e: 'io' },
  { t0: 5.95, t1: T_RESUME, rel: 1, a: { x: 170, y: -600, z: 1.8 }, b: { x: -150, y: -690, z: 2.4 }, e: 'l' },          // one slow monotonic dolly across the car
  { t0: T_RESUME, t1: 16.0, rel: 1, a: { x: -150, y: -690, z: 2.4 }, b: { x: 130, y: -600, z: 2.0 }, e: 'io' },
  { t0: 16.0, t1: 16.3, a: { x: CRASHX, y: -560, z: 2.0 }, b: { x: -150, y: -420, z: 1.35 }, e: 'io' },
  { t0: 16.3, t1: 16.66, a: { x: 40, y: -440, z: 1.7 }, b: { x: 60, y: -450, z: 1.8 } },
  { t0: 16.66, t1: 17.55, a: { x: -90, y: -440, z: 1.4 }, b: { x: -110, y: -450, z: 1.48 }, e: 'io' },
  { t0: 17.55, t1: 17.93, a: { x: -110, y: -450, z: 1.48 }, b: { x: 0, y: -330, z: 1.3 }, e: 'io' },
  { t0: 17.93, t1: 18.2, a: { x: 0, y: -330, z: 1.3 } },
];
const camRaw = K.camera(shots, []);
const camAt = t => { const c = camRaw(t); if (t > 5.95 && t < 16.0) { const w = K.sm((t - 5.95) / .6) * K.sm((16.0 - t) / .6); c.y += Math.sin((t - 5.95) * 2.4) * 22 * w; c.x += Math.sin((t - 5.95) * 1.7) * 30 * w; }   /* slow float */ if (c.shot.rel) c.x += carX(simT(t)); if (c.shot.relG) { let gx = 0; for (let k = 0; k < 6; k++) gx += ground(g(t - k * .025)).x; c.x += gx / 6; }   // follows his hips, slightly lagged
  for (const im of IMP) if (im.k !== 'small') { const s = simT(t) - im.t; if (s > 0 && s < .3) { const e = Math.exp(-s * 14) * (im.k === 'big' ? 22 : 10) / c.z; c.x += Math.sin(s * 70) * e; c.y += Math.cos(s * 55) * e * .7; } }
  return c; };
// ---------- drawing ----------
function ground(p) {
  const q = Object.assign({}, p); q.sx = (p.sx || 1) * Math.cos((p.yaw || 0) * Math.PI / 180); if (Math.abs(q.sx) < .32) q.sx = .32 * Math.sign(q.sx || 1);   // turn never goes paper-thin
  if (p.ya > 0) { q.y = -p.ya; return q; }
  const z = Object.assign({}, q, { y: 0 }), J = K.joints(z); q.y = -Math.max(J.fa[1], J.fb[1]) - 9 + (p.y || 0); return q;
}
const lagOf = (trk, t) => { let lx = 0, ly = 0; for (let k = 1; k <= 10; k++) { const a = ground(trk(t - k / 60)), b = ground(trk(t - k / 60 - 1 / 60));
  const w = Math.exp(-k / 4) * Math.cos(k * .7) * .06; lx -= (a.x - b.x) * 60 * w * .1; ly -= (a.y - b.y) * 60 * w * .1; } return [K.clamp(lx, -40, 40), K.clamp(ly, -40, 40)]; };
const blinkAt = t => ((t * 1000) % 3100) < 110;
const mouthAt = t => LOUD[Math.round(t * 60)] || 0;
function fighter(c, trk, t, kind) {
  const p = ground(trk(t)), prev = ground(trk(t - 2 / 60));
  const sm = K.joints(prev);
  K.shadow(c, p.x, 120, .45 * K.clamp(1 + (p.y + 270) / 400, 0, 1));
  K.drawFighter(c, p, { kind, lag: lagOf(trk, t), smear: sm, mouth: kind === 'guy' && p.turn > .6 ? mouthAt(t) : 0, blink: blinkAt(t), brow: p.turn > .6 ? .5 : 0 });
}
function occupant(c, t) {
  const p = Object.assign({}, seat(t)), pay = t < T_RESUME ? 0 : K.sm((t - T_RESUME - .1) / .5) * 16;
  c.fillStyle = '#2c3760'; c.beginPath(); c.roundRect(-150, -235, 260, 70, 26); c.fill();
  c.save(); c.translate(-110, -210); c.rotate(-.2); c.fillStyle = '#3c4a78'; c.beginPath(); c.roundRect(-40, -300, 80, 320, 34); c.fill(); c.beginPath(); c.roundRect(-34, -375, 66, 80, 22); c.fill(); c.restore();
  c.fillStyle = '#4a4f66'; c.fillRect(-196, -480, 28, 360); c.fillStyle = '#7f8696'; c.beginPath(); c.roundRect(-214, -170, 60, 60, 12); c.fill();
  c.strokeStyle = '#1c1f2c'; c.lineWidth = 16; c.lineCap = 'round'; c.beginPath(); c.moveTo(250, -390); c.lineTo(205, -270); c.stroke(); c.beginPath(); c.moveTo(232, -330); c.lineTo(300, -300); c.stroke();
  const J = K.drawFighter(c, p, { kind: 'guy', mouth: p.turn > .5 ? mouthAt(t) : 0, blink: blinkAt(t), thumb: t > 15.75 && t < 16.2, brow: t > 5.2 && t < 13 ? .5 : 0, lag: [0, 0] });
  const bag = airbagAt(t); if (bag > 0) K.airbag(c, 228, -340, bag, 1);
  const buckled = t >= 3.9, locked = t >= T_CRASH && t < T_RESUME + .7;
  const sh = [J.chest[0] + 6, J.chest[1] + 16], hp = [J.hip[0] + 34, J.hip[1] + 6];
  c.save(); if (locked && t > T_FREEZE) { c.shadowColor = '#ffb347'; c.shadowBlur = 26; }
  c.strokeStyle = '#ffb347'; c.lineWidth = 17; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath(); c.moveTo(-182, -440 - pay); c.lineTo(-182, -150); c.stroke();
  if (buckled) { c.beginPath(); c.moveTo(-182, -440 - pay); c.lineTo(sh[0], sh[1]); c.quadraticCurveTo((sh[0] + hp[0]) / 2 + 26, (sh[1] + hp[1]) / 2, hp[0], hp[1]); c.lineTo(-120, -205); c.stroke(); }
  else if (t >= 3.74) { const u = K.clamp((t - 3.74) / .16, 0, 1), hx = K.lerp(-182, J.ha[0], 1), hy = J.ha[1]; c.beginPath(); c.moveTo(-182, -440); c.lineTo(hx, hy); c.stroke(); }
  c.restore();
  c.fillStyle = '#c9ced8'; c.beginPath(); c.roundRect(-196, -456 - pay, 30, 26, 6); c.fill(); if (buckled) { c.beginPath(); c.roundRect(hp[0] - 12, hp[1] - 14, 30, 22, 6); c.fill(); }
}
function impactShape(c, im, a) {   // clean flat impact star, 4 frames, no rings
  if (a < 0 || a > 4 / 60) return; const u = a / (4 / 60), R = (im.k === 'small' ? 70 : 120) * (1 + .4 * u);
  c.save(); c.translate(im.p[0], im.p[1]); c.globalAlpha = 1 - u * .7; c.fillStyle = '#fff6e4'; c.beginPath();
  for (let i = 0; i < 16; i++) { const ang = i / 16 * Math.PI * 2, rr = i % 2 ? R * .35 : R; c.lineTo(Math.cos(ang) * rr, Math.sin(ang) * rr); } c.closePath(); c.fill(); c.restore();
}
function world(c, t, cm) {
  const st = simT(t);
  K.drawStreet2(c, L, cm, st);
  c.save(); K.apply(c, cm);
  K.barrier2(c, BARX);
  const inCar = t >= T_IN && t < T_BACK;
  const cx = carX(st);
  K.drawCar(c, cx, -1, { crush: crushAt(t), pitch: pitchAt(t), spin: (CAR0 - cx) / K.CAR.wheel, doorOff: t >= T_FREEZE && t < T_BACK, glass: .22, col: '#2a9fb4', col2: '#7fe0ea', col3: '#1d5f73',
    occupant: inCar ? (cc => occupant(cc, t)) : null });
  if (t >= T_FREEZE && t < T_BACK) { c.save(); c.translate(cx, 0); c.scale(-1, 1); c.strokeStyle = 'rgba(127,224,234,.5)'; c.setLineDash([16, 12]); c.lineWidth = 5; c.strokeRect(-340, -395, 640, 225); c.restore(); }
  if (!(t > 4.3 && t < 16.0)) fighter(c, r, st, 'rival');
  if (!inCar) fighter(c, g, t, 'guy');
  for (const im of IMP) if (im.k !== 'big') impactShape(c, im, st - im.t);
  c.restore();
  K.drawFg(c, L, cm);
}
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
const blink2 = 0;
let vig = null;
function makeVig() { const v = document.createElement('canvas'); v.width = K.W; v.height = K.H; const x = v.getContext('2d');
  const g = x.createRadialGradient(K.W / 2, K.H * .5, K.H * .3, K.W / 2, K.H * .5, K.H * .75); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(8,6,20,.5)'); x.fillStyle = g; x.fillRect(0, 0, K.W, K.H); return v; }
S.init = d => {
  const cv = document.getElementById('c'); ctx = cv.getContext('2d');
  wc = document.createElement('canvas'); wc.width = K.W * SS; wc.height = K.H * SS; wx = wc.getContext('2d');
  L = K.buildStreet2(-9500, 2500); vig = makeVig();
  WORDS = d.words; LOUD = d.loud; CH = chunks();
  S.T = { v1: wordAt('your'), tighten: wordAt('tighten'), v2: wordAt('in'), crashW: wordAt('crash'), charge: wordAt('charge'), motor: wordAt('motor'), v3: wordAt('snug') - .3, v4: wordAt('then') };
  S.events = { impacts: IMP.map(i => ({ t: i.t, s: i.s })), whoosh: WHOOSH, crash: T_CRASH, freeze: T_FREEZE, go: T_GO, click: 3.9, plop: T_IN + .1, airbag: 13.42, land: [17.1], resume: T_RESUME, T: S.T };
};
const fastAt = t => STRIKES.some(s => t > s - .12 && t < s + .04) || (t > 2.84 && t < 3.6) || (t > T_GO && t < T_CRASH + .02) || (t > 16.0 && t < 16.32);
S.frame = (f, fps) => {
  const t = f / fps, n = fastAt(t) ? 4 : 1, frozen = t >= T_FREEZE && t < T_RESUME;
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.filter = 'none';
  for (let k = 0; k < n; k++) {
    const ts = n === 1 ? t : t + ((k + .5) / n - .5) * .5 / fps, cm = camAt(ts);
    wx.setTransform(SS, 0, 0, SS, 0, 0); world(wx, ts, cm);
    ctx.globalAlpha = 1 / (k + 1); ctx.filter = frozen ? 'saturate(.85) brightness(.97)' : 'none';
    ctx.imageSmoothingQuality = 'high'; ctx.drawImage(wc, 0, 0, K.W, K.H);
  }
  ctx.globalAlpha = 1; ctx.filter = 'none';
  // ONE full-frame colour flash per big hit (4 frames)
  for (const im of IMP) if (im.k === 'big') { const k = Math.round((t - im.t) * fps); if (k >= 0 && k < 4) { ctx.fillStyle = `rgba(255,236,200,${[.72, .42, .18, .06][k]})`; ctx.fillRect(0, 0, K.W, K.H); } }
  ctx.drawImage(vig, 0, 0);
  if (t >= T_FREEZE && t < 5.6) { ctx.save(); ctx.globalAlpha = K.clamp((t - T_FREEZE) / .08, 0, 1) * K.clamp((5.6 - t) / .25, 0, 1) * .95; ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.roundRect(80, 330, 34, 100, 10); ctx.roundRect(136, 330, 34, 100, 10); ctx.fill(); ctx.restore(); }
  diagrams(ctx, t); limiterCard(ctx, t); headline(ctx, t); captions(ctx, t);
  if (t >= 16.92 && t < 17.62) K.poll(ctx, 160, 300, Math.min((t - 16.92) / .2, (17.62 - t) / .14), t > 17.25 ? 1 : 0);
  tag(ctx);
};
window.SCENE = S;
})();
