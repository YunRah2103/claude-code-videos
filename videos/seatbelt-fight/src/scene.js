// seatbelt-fight scene (inkfight kit). Rendered by shared/assets/inkfight/render.mjs. One street, one continuous camera:
// 0-3.4 fight (dash clash, spin kick + backflip, 3-hit combo, body blow, dive kick + ground crack, fist clash shockwave)
// 3.5-4.3 a car skids in and stops abruptly right behind him | 4.55 freeze, push into the driver's locked belt
// 4.8 "Quick pause." | 5.7-12.7 diagrams | 12.7-15.3 time resumes: force limiter eases the driver back, thumbs up,
// car reverses away | 15.5-18 fight resumes, last hit, "Did you know that?" + poll, back to frame 1 for the loop.
(function () {
const S = {}; let ctx, wc, wx, street, post, WORDS = [], LOUD = [];
const G0 = { x: -190, y: 0, face: 1, lean: 8, head: -6, a1: 38, a2: 112, b1: 58, b2: 118, l1: 24, l2: -20, m1: -18, m2: 14, turn: 0, s: 1, sx: 1, sy: 1, rot: 0 };
const R0 = { x: 190, y: 0, face: -1, lean: 10, head: -4, a1: 42, a2: 108, b1: 60, b2: 114, l1: 24, l2: -20, m1: -18, m2: 14, s: 1, sx: 1, sy: 1, rot: 0 };
const BLOCK = { a1: 78, a2: 128, b1: 88, b2: 122 };
const CROUCH = { l1: 62, l2: -110, m1: -8, m2: -74 };
const RUN = { l1: 60, l2: -30, m1: -55, m2: -60 };
const HS = 1 / 60, T_STOP = 4.30, T_FREEZE = 4.55, T_RESUME = 12.72;
const STOPX = -330 - 740;                       // car centre when stopped: bumper 70 px behind him
const hold = (t, n) => [t + n * HS, {}, 'l'];
// ---------- fighters (hand-keyed; hit-stops = held keys) ----------
const g = K.track([
  [0, G0],
  [.08, Object.assign({ x: -205, lean: -12, head: 0, a1: 20, a2: 130 }, CROUCH), 'io'],                      // anticipation
  [.22, Object.assign({ x: -70, y: -20, lean: 30, a1: 105, a2: 55, b1: 70, b2: 100 }, RUN), 'o'], hold(.22, 3), // dash + parry
  [.36, { x: -120, y: 0, lean: -8, l1: 24, l2: -20, m1: -18, m2: 14, a1: 50, a2: 100 }, 'o'],
  [.44, { lean: 12, sx: 1, a1: 20, a2: 120, b1: 20, b2: 120 }, 'io'],                                            // spin heel kick
  [.50, { sx: 0, x: -110, y: -40, l1: 50, l2: -60 }, 'l'], [.55, { sx: -1, y: -70 }, 'l'], [.59, { sx: 0 }, 'l'],
  [.64, { sx: 1, y: -60, lean: -32, l1: 112, l2: 0, m1: -10, m2: -20, a1: -50, a2: 20, b1: 150, b2: 10 }, 'o'],
  [.74, Object.assign({}, G0, { x: -120, y: 0 }), 'io'],
  [.78, Object.assign({ lean: 20, a1: 10, a2: 60, b1: -10, b2: 40 }, CROUCH), 'i'],                               // backflip dodge
  [.88, { x: -240, y: -280, rot: 180, l1: 95, l2: -140, m1: 85, m2: -140, a1: 120, a2: 60, b1: 110, b2: 60, lean: 0 }, 'o'],
  [1.00, Object.assign({ x: -300, y: 0, rot: 360, lean: 22, a1: 40, a2: 100, b1: 60, b2: 110 }, CROUCH), 'i'], [1.001, { rot: 0 }, 'h'],
  [1.06, Object.assign({}, G0, { x: -290 }), 'o'],
  [1.12, Object.assign({ x: -295, lean: -6 }, BLOCK), 'o'], hold(1.12, 2),                                     // blocks the 3-hit combo
  [1.20, { x: -300, lean: 2 }], [1.24, { x: -310, lean: -8, head: -8 }, 'o'], hold(1.24, 2),
  [1.32, { lean: 2 }], [1.40, { x: -335, lean: -16, head: -14 }, 'o'], hold(1.40, 2),
  [1.52, Object.assign({ x: -340, lean: 42, head: 10, a1: 10, a2: 120, b1: 40, b2: 110 }, CROUCH), 'io'],        // dips under, coils
  [1.64, { x: -280, lean: 30, head: 0, a1: 76, a2: 14, b1: 20, b2: 120, l1: 48, l2: -12, m1: -46, m2: 8 }, 'o'], hold(1.64, 4), // body blow
  [1.84, { x: -270, lean: 14, a1: 60, a2: 50 }, 'o'],
  [2.06, Object.assign({}, G0, { x: -260 })],
  [2.28, Object.assign({ x: -265, lean: -4 }, BLOCK, CROUCH), 'io'],                                             // braces for the dive kick
  [2.42, { x: -285, sy: .84, sx: 1.12, lean: -10, head: -14, l1: 70, l2: -120, m1: -20, m2: -90 }, 'o'], hold(2.42, 3),
  [2.62, Object.assign({ x: -420, sy: 1, sx: 1, lean: 6 }, BLOCK, { l1: 40, l2: -40, m1: -30, m2: 0 }), 'o'],     // skids back
  [2.72, Object.assign({ x: -400, lean: -18, a1: -10, a2: 150, b1: 70, b2: 110 }, CROUCH), 'io'],                // charge
  [2.90, Object.assign({ x: -150, lean: 30, a1: -20, a2: 140, b1: 80, b2: 80 }, RUN), 'l'],
  [2.98, { x: -66, lean: 26, a1: 92, a2: 2, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8 }, 'o'], hold(2.98, 4), // fist clash
  [3.40, { x: -255, lean: -6, a1: 60, a2: 100, l1: 30, l2: -10, m1: -30, m2: 10 }, 'o'],                       // shockwave slide
  [3.58, Object.assign({}, G0, { x: -255 })],
  [3.75, { turn: .55, head: 14 }, 'io'],                                                                          // hears the screech
  [4.12, { turn: .3, head: 8 }],
  [T_STOP, { lean: 22, head: 14, turn: .4, a1: 160, a2: 40, b1: 150, b2: 50, sx: .94, l1: 40, l2: -40 }, 'o'],     // flinch
  [T_FREEZE, { turn: .45 }], [4.58, {}],
  [4.84, { x: -820, turn: 1, head: 0, lean: 2, sx: 1, a1: 20, a2: 30, b1: 14, b2: 20, l1: 12, l2: -6, m1: -12, m2: 6 }, 'back'],
  // presenter gestures: points back at the driver's belt, then talks with his hands
  [5.6, { a1: -95, a2: 10 }, 'o'], [6.6, { a1: -80, a2: 30 }], [7.3, { a1: 40, a2: 90, b1: 30, b2: 80 }],
  [8.1, { a1: -100, a2: 5, b1: 14, b2: 20 }, 'o'], [9.2, { a1: 50, a2: 100 }], [9.9, { a1: -90, a2: 20 }, 'o'],
  [10.8, { a1: 45, a2: 95, b1: 35, b2: 90 }], [11.6, { a1: -95, a2: 10, b1: 14, b2: 20 }, 'o'], [12.5, { a1: 20, a2: 30 }],
  [13.2, { turn: .2, head: 10 }], [14.35, { a1: 160, a2: 30 }, 'back'],                                            // thumbs up back
  [14.9, { a1: 120, a2: 80 }], [15.1, { a1: 150, a2: 30 }], [15.3, { a1: 120, a2: 80 }],                           // waves the car off
  [15.55, Object.assign({}, G0, { x: -255 }), 'io'],
  [15.78, Object.assign({ x: -270, lean: -14, a1: 18, a2: 140 }, CROUCH), 'io'],
  [16.05, Object.assign({ x: -170, lean: 30, a1: -10, a2: 140 }, RUN), 'l'],
  [16.15, { x: -140, lean: 26, a1: 70, a2: 2, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8, head: -4 }, 'o'], hold(16.15, 4),
  [16.32, { lean: 10, a1: 55, a2: 60 }, 'o'],
  [16.55, { x: -160, lean: 0, head: 0, turn: 1, a1: 40, a2: 90, b1: 22, b2: 40, l1: 12, l2: -6, m1: -12, m2: 6 }, 'io'],
  [16.8, { a1: 48, a2: 100 }], [17.1, { a1: 40, a2: 90 }], [17.45, {}],
  [17.62, { turn: 0 }, 'io'], [17.92, Object.assign({}, G0)], [18.2, Object.assign({}, G0)],
]);
const r = K.track([
  [0, R0],
  [.08, Object.assign({ x: 215, lean: -10, a1: 30, a2: 120 }, CROUCH), 'io'],
  [.22, { x: 60, y: -120, lean: 12, l1: 100, l2: -135, m1: -30, m2: -60, a1: -30, a2: 40, b1: 150, b2: 20 }, 'o'], hold(.22, 3), // flying knee
  [.36, Object.assign({}, R0, { x: 175 }), 'o'],
  [.52, Object.assign({ x: 150, lean: 62, head: 12, a1: 30, a2: 120 }, { l1: 80, l2: -112, m1: -40, m2: -80 }), 'o'], // ducks the heel
  [.72, { lean: 46, a1: -20, a2: 130 }, 'io'],
  [.84, { x: 30, y: -70, lean: -10, head: -8, a1: 172, a2: 12, l1: 26, l2: -10, m1: -26, m2: 6 }, 'o'],             // rising uppercut (whiffs)
  [1.00, Object.assign({}, R0, { x: 60 }), 'io'],
  [1.12, { x: 30, lean: 22, a1: 92, a2: 2 }, 'o'], hold(1.12, 2), [1.20, { a1: 45, a2: 100, lean: 10 }],       // jab
  [1.24, { lean: 24, b1: 96, b2: 2 }, 'o'], hold(1.24, 2), [1.32, { b1: 60, b2: 114, lean: 8, x: 40 }],        // jab
  [1.40, { x: 20, lean: 30, a1: 100, a2: 70, sx: .9 }, 'o'], hold(1.40, 2),                                      // hook
  [1.52, { lean: 18, sx: 1 }],
  [1.64, { x: 40, lean: 56, head: 22, sx: .85, sy: 1.04, a1: 10, a2: 40, b1: 20, b2: 30 }, 'o'], hold(1.64, 4),   // doubled over
  [1.95, Object.assign({ x: 360, lean: 30, head: 10, sx: 1, sy: 1 }, CROUCH), 'o'],                                // slides back
  [2.08, Object.assign({ x: 330, lean: 24, a1: 20, a2: 110 }, CROUCH), 'io'],
  [2.26, { x: 120, y: -460, lean: -16, l1: 100, l2: -130, m1: 30, m2: -110, a1: 150, a2: 30, b1: 130, b2: 40 }, 'o'], // leap
  [2.42, { x: -110, y: -170, lean: -42, l1: 52, l2: 0, m1: -20, m2: -60, a1: 170, a2: 0 }, 'i'], hold(2.42, 3),   // dive kick
  [2.56, { x: 120, y: -330, rot: 200, l1: 90, l2: -140, m1: 80, m2: -140 }, 'o'],                                // backflips away
  [2.70, Object.assign({ x: 560, y: 0, rot: 360, lean: 20, a1: 20, a2: 130 }, CROUCH), 'o'], [2.701, { rot: 0 }, 'h'],
  [2.90, Object.assign({ x: 330, lean: 30, a1: -20, a2: 140, b1: 80, b2: 80 }, RUN), 'l'],
  [2.98, { x: 410, lean: 26, a1: 92, a2: 2, b1: 30, b2: 120, l1: 46, l2: -12, m1: -42, m2: 8 }, 'o'], hold(2.98, 4),
  [3.40, { x: 660, lean: -6, a1: 60, a2: 100, l1: 30, l2: -10, m1: -30, m2: 10 }, 'o'],
  [3.6, Object.assign({}, R0, { x: 660 })], [T_RESUME, {}], [15.5, {}],
  [15.78, Object.assign({ x: 640, lean: -10 }, CROUCH), 'io'], [16.05, Object.assign({ x: 290, lean: 28, a1: 92, a2: 40 }, RUN), 'l'],
  [16.15, Object.assign({}, R0, { x: 205, lean: -30, head: -26, sx: .9, sy: 1.06 }), 'o'], hold(16.15, 4),
  [16.40, { x: 560, y: -170, rot: -140, sx: 1, sy: 1, l1: 80, l2: -90, m1: 60, m2: -100, a1: 160, a2: 20, b1: 140, b2: 30 }, 'o'],
  [16.62, { x: 650, y: 0, rot: 0, lean: -18, head: 6, l1: 86, l2: -8, m1: 80, m2: -14, a1: -30, a2: 10, b1: -40, b2: 10 }, 'o'],
  [17.10, { head: -6 }], [17.30, Object.assign({ lean: 30, x: 640, a1: 10, a2: 60 }, CROUCH), 'io'],
  [17.50, { x: 420, y: -200, lean: 0, l1: 50, l2: -80, m1: 20, m2: -70, a1: 130, a2: 20, b1: 120, b2: 20 }, 'o'],
  [17.76, Object.assign({}, R0, { x: 196 }), 'io'], [17.92, Object.assign({}, R0)], [18.2, Object.assign({}, R0)],
]);
// driver (car-local coords, faces the car's front): neutral stickman, cap
const DRV = { abs: 1, x: 30, y: -200, face: 1, lean: -12, head: 4, a1: 82, a2: 12, b1: 78, b2: 18, l1: 84, l2: -82, m1: 80, m2: -78, s: .9, sx: 1, sy: 1 };
const drv = K.track([
  [0, DRV], [4.08, {}], [4.14, { lean: -2 }], [T_STOP, { lean: 26, head: 18, a1: 98, a2: 0, b1: 92, b2: 4 }, 'o'], [T_FREEZE, { lean: 27, head: 19 }],
  [T_RESUME, {}], [T_RESUME + .5, { lean: 31, head: 20 }, 'io'],                 // force limiter: belt pays out a little
  [T_RESUME + 1.2, { lean: -8, head: 2 }, 'io'], [14.2, { a1: 150, a2: 30 }, 'back'], [14.75, { a1: 82, a2: 12 }], [16, {}],
]);
// ---------- car: skids in from the left, stops abruptly 70 px behind him; reverses away after the explainer ----------
const carX = t => {
  if (t < T_STOP - .2) return STOPX - 420 - 4200 * (T_STOP - .2 - t);
  if (t < T_STOP) { const u = (t - (T_STOP - .2)) / .2; return STOPX - 420 * (1 - u) * (1 - u); }
  if (t < 14.85) return STOPX;
  return STOPX - 3200 * Math.pow((t - 14.85) / .7, 2);
};
const simT = t => t >= T_FREEZE && t < T_RESUME ? T_FREEZE : t;
const pitch = t => { t = simT(t); if (t < T_STOP - .2) return 0; if (t < T_STOP) return 4 * K.sm((t - T_STOP + .2) / .2);
  if (t < T_RESUME) return 4 * Math.exp(-(t - T_STOP) * 7) * Math.cos((t - T_STOP) * 26);
  if (t < 14.85) return 4 * Math.exp(-(T_FREEZE - T_STOP) * 7) * Math.cos((T_FREEZE - T_STOP) * 26) * Math.exp(-(t - T_RESUME) * 5);
  return -1.5 * K.sm((t - 14.85) / .2); };
// ---------- impacts ----------
const IMP = [
  { t: .22, p: [-10, -500], sh: 22, fl: .6, s: 'block', zp: .08 },
  { t: 1.12, p: [-190, -470], sh: 8, fl: .25, s: 'block', sm: 1 },
  { t: 1.24, p: [-190, -455], sh: 8, fl: .25, s: 'block', sm: 1 },
  { t: 1.40, p: [-200, -500], sh: 14, fl: .4, s: 'punch', zp: .05 },
  { t: 1.64, p: [-30, -360], sh: 32, fl: .9, s: 'punch_big', zp: .12 },
  { t: 2.42, p: [-230, -560], sh: 40, fl: .9, inv: 1, s: 'clash', zp: .12, crack: -285 },
  { t: 2.98, p: [180, -500], sh: 48, fl: 1, inv: 1, s: 'clash', zp: .16, wave: 1 },
  { t: T_STOP, p: [-420, -150], sh: 30, fl: .5, s: 'stop', zp: .06 },
  { t: 16.15, p: [150, -560], sh: 34, fl: 1, inv: 1, s: 'punch_big', zp: .12 },
];
const WHOOSH = [.12, .46, .56, .80, .86, 1.36, 1.58, 2.18, 2.36, 2.84, 3.08, 15.98, 16.38, 17.42];
// ---------- camera: one continuous move through the car stop ----------
const shots = [
  { t0: 0, t1: .22, a: { x: 0, y: -380, z: 1.32 }, b: { x: 20, y: -420, z: 1.45 }, e: 'i' },
  { t0: .22, t1: .46, a: { x: 20, y: -440, z: 1.75, r: .02 }, b: { x: -30, y: -430, z: 1.6, r: .02 }, e: 'o' },
  { t0: .46, t1: 1.04, a: { x: -60, y: -330, z: 1.55, r: -.04 }, b: { x: -150, y: -360, z: 1.35, r: -.03 } },
  { t0: 1.04, t1: 1.58, a: { x: -150, y: -450, z: 1.9 }, b: { x: -130, y: -450, z: 2.05 } },
  { t0: 1.58, t1: 2.12, a: { x: -120, y: -420, z: 1.5, r: .025 }, b: { x: 20, y: -400, z: 1.35, r: .02 }, e: 'o' },
  { t0: 2.12, t1: 2.62, a: { x: -40, y: -560, z: .95 }, b: { x: -200, y: -420, z: 1.15 }, e: 'io' },
  { t0: 2.62, t1: 2.92, a: { x: -20, y: -420, z: 1.2 }, b: { x: 130, y: -470, z: 1.6 }, e: 'i' },
  { t0: 2.92, t1: 3.06, a: { x: 175, y: -500, z: 3.0 }, b: { x: 175, y: -500, z: 3.3 } },
  { t0: 3.06, t1: 3.62, a: { x: 175, y: -500, z: 3.3 }, b: { x: -300, y: -440, z: 1.15 }, e: 'o' },
  { t0: 3.62, t1: T_STOP, a: { x: -300, y: -440, z: 1.15 }, b: { x: -700, y: -560, z: .78 }, e: 'io' },
  { t0: T_STOP, t1: 4.58, a: { x: -700, y: -560, z: .78 }, b: { x: -1030, y: -420, z: 2.3 }, e: 'io' },
  { t0: 4.58, t1: 4.72, a: { x: -1030, y: -420, z: 2.3 }, b: { x: -1010, y: -410, z: 2.45 }, e: 'o' },
  { t0: 4.72, t1: 5.4, a: { x: -1010, y: -410, z: 2.45 }, b: { x: -760, y: -947, z: .95 }, e: 'io' },
  { t0: 5.4, t1: T_RESUME, a: { x: -760, y: -947, z: .95 }, b: { x: -770, y: -940, z: .99 }, e: 'l' },
  { t0: T_RESUME, t1: 15.2, a: { x: -770, y: -940, z: .99 }, b: { x: -700, y: -900, z: 1.02 }, e: 'io' },
  { t0: 15.2, t1: 15.9, a: { x: -700, y: -900, z: 1.02 }, b: { x: -20, y: -430, z: 1.25 }, e: 'io' },
  { t0: 15.9, t1: 16.32, a: { x: -20, y: -430, z: 1.25 }, b: { x: 20, y: -460, z: 1.6 }, e: 'i' },
  { t0: 16.32, t1: 17.5, a: { x: -60, y: -440, z: 1.35 }, b: { x: -80, y: -450, z: 1.45 }, e: 'io' },
  { t0: 17.5, t1: 17.92, a: { x: -80, y: -450, z: 1.45 }, b: { x: 0, y: -380, z: 1.32 }, e: 'io' },
  { t0: 17.92, t1: 18.1, a: { x: 0, y: -380, z: 1.32 } },
];
const camRaw = K.camera(shots, IMP.map(i => ({ t: i.t, shake: i.sh })));
const camAt = t => { const c = camRaw(t);
  for (const im of IMP) if (im.zp) { const a = simT(t) - im.t; if (a >= 0 && a < .35) c.z *= 1 + im.zp * Math.exp(-a * 12); }   // impact punch-in
  return c; };
// ---------- drawing ----------
function ground(p) { if (p.abs) return p; const q = Object.assign({}, p, { y: 0 }); const J = K.joints(q); const low = Math.max(J.fa[1], J.fb[1]); return Object.assign(p, { y: -low - 9 + p.y }); }
const blinkAt = t => ((t * 1000) % 2900) < 110;
const mouthAt = t => LOUD[Math.round(t * 60)] || 0;
function fighter(c, trk, t, isG) {
  const p = ground(trk(t)), J = K.joints(p);
  if (!(t > T_FREEZE && t < T_RESUME)) for (const key of ['ha', 'hb', 'fa', 'fb']) {
    const pts = []; for (let k = 0; k < 8; k++) pts.push(K.joints(ground(trk(t - k / 60)))[key]);
    K.smear(c, pts, 40, isG ? 'rgba(255,240,220,.9)' : 'rgba(255,90,70,.9)');
  }
  K.shadow(c, J.hip[0], 130, .5 * K.clamp(1 + p.y / 300, 0, 1));
  if (isG) K.drawGuy(c, p, { mouth: p.turn > .6 ? mouthAt(t) : 0, blink: blinkAt(t), thumb: t > 14.3 && t < 14.9, brow: p.turn > .6 ? .5 : 0 });
  else K.drawRival(c, p, { t });
}
function occupant(c, t) {   // car-local coords (x forward): seat, pillar + retractor, wheel, driver, belt
  const p = Object.assign({}, drv(simT(t)));
  const pay = t < T_RESUME ? 0 : K.sm((t - T_RESUME - .1) / .5) * 18;
  c.fillStyle = '#2c3760'; c.beginPath(); c.roundRect(-150, -235, 260, 70, 26); c.fill();
  c.save(); c.translate(-110, -210); c.rotate(-.2); c.fillStyle = '#3c4a78'; c.beginPath(); c.roundRect(-40, -300, 80, 320, 34); c.fill(); c.beginPath(); c.roundRect(-34, -375, 66, 80, 22); c.fill(); c.restore();
  c.fillStyle = '#4a4f66'; c.fillRect(-196, -480, 28, 360);
  c.fillStyle = '#7f8696'; c.beginPath(); c.roundRect(-214, -170, 60, 60, 12); c.fill();
  c.strokeStyle = '#1c1f2c'; c.lineWidth = 16; c.lineCap = 'round'; c.beginPath(); c.moveTo(250, -390); c.lineTo(205, -270); c.stroke();
  c.beginPath(); c.moveTo(232, -330); c.lineTo(300, -300); c.stroke();
  const J = K.joints(p);
  K.drawRival(c, p, { pal: { red: '#e9dcc4', redD: '#b9a98f' }, band: false, cap: '#3b4a7a', rim: 'rgba(255,190,110,.7)', thumb: t > 14.2 && t < 14.8 });
  const locked = t >= T_STOP - .02 && t < T_RESUME + 1.2, slack = t < T_STOP - .1 ? .3 : 0;
  const sh = [J.chest[0] + 6, J.chest[1] + 16], hp = [J.hip[0] + 34, J.hip[1] + 6];
  c.save(); if (locked && t > T_FREEZE) { c.shadowColor = '#ffb347'; c.shadowBlur = 34; }
  c.strokeStyle = '#ffb347'; c.lineWidth = 17; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath(); c.moveTo(-182, -440 - pay); c.lineTo(sh[0], sh[1]);
  c.quadraticCurveTo((sh[0] + hp[0]) / 2 + 26 + slack * 40, (sh[1] + hp[1]) / 2, hp[0], hp[1]); c.lineTo(-120, -205); c.stroke();
  c.beginPath(); c.moveTo(-182, -440 - pay); c.lineTo(-182, -150); c.stroke(); c.restore();
  c.fillStyle = '#c9ced8'; c.beginPath(); c.roundRect(-196, -456 - pay, 30, 26, 6); c.fill(); c.beginPath(); c.roundRect(hp[0] - 12, hp[1] - 14, 30, 22, 6); c.fill();
}
function world(c, t, cm) {
  const st = simT(t);
  K.drawStreet(c, street, cm, st);
  const cx = carX(t), carOn = cx > -6000;
  // headlight glare sweeping in before the car
  if (st > 3.5 && st < T_STOP + .3) { const a = K.clamp((st - 3.5) / .4, 0, 1) * .55, hx = cx + 740;
    const gg = c.createRadialGradient(hx, -260, 10, hx, -260, 900); gg.addColorStop(0, `rgba(255,244,210,${a})`); gg.addColorStop(1, 'rgba(255,244,210,0)'); c.fillStyle = gg; c.fillRect(hx - 900, -1160, 1800, 1800); }
  // skid marks + tyre smoke while braking
  if (carOn && st > T_STOP - .22) { c.fillStyle = 'rgba(8,8,14,.6)'; c.fillRect(STOPX - 450 + 160, 6, 420, 9); c.fillRect(STOPX + 430 - 420, 6, 420, 9);
    for (let k = 0; k < 16; k++) { const a = st - (T_STOP - .2) - k * .015; if (a < 0) continue; const u = Math.min(a / 1.2, 1);
      for (const wx of [STOPX - 440, STOPX + 430]) { c.fillStyle = `rgba(200,205,220,${.4 * (1 - u)})`; c.beginPath(); c.arc(wx - 60 - k * 18 - a * 120, -50 - a * 140 - k * 4, 40 + a * 160, 0, 7); c.fill(); } } }
  if (carOn && cx > -3800) {
    const cut = t >= T_STOP + .1 && t < 15.2;
    K.drawCar(c, cx, 1, { pitch: pitch(t), spin: (cx - STOPX) / K.CAR.wheel, doorOff: cut, glass: cut ? .08 : .25, col: '#2a9fb4', col2: '#7fe0ea', occupant: cc => occupant(cc, t) });
    if (cut) { c.save(); c.translate(cx, 0); c.strokeStyle = 'rgba(127,224,234,.55)'; c.setLineDash([16, 12]); c.lineWidth = 5; c.strokeRect(-340, -395, 640, 225); c.restore(); }
    if (st < T_STOP) K.speedLines(c, cx, -300, st, 9, 1, 500);
  }
  fighter(c, r, st, false); fighter(c, g, t, true);
  IMP.forEach((im, k) => { const a = st - im.t;
    if (im.s !== 'stop') { K.burst(c, im.p[0], im.p[1], a, im.sm ? 110 : 190, 11 + k); K.sparks(c, im.p[0], im.p[1], a, im.sm ? 10 : 22, 31 + k, 900); }
    else K.dust(c, STOPX + 600, -20, a, 14, 5, 80, 1);
    if (im.crack !== undefined) { K.crack(c, im.crack, a, 4); K.dust(c, im.crack, -10, a, 12, 9, 70); }
    if (im.wave) { K.shockwave(c, im.p[0], im.p[1], a, 900); K.dust(c, -66, -10, a, 10, 21, 60, -1); K.dust(c, 410, -10, a, 10, 22, 60, 1); }
  });
  [[.36, -120], [1.00, -300], [2.62, -420], [2.70, 560], [16.62, 650]].forEach(([tt, x], k) => K.dust(c, x, -10, st - tt, 8, 70 + k, 50));
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
  const H = [[S.T.v1, S.T.v2, 'MEET THE PRETENSIONER'], [S.T.v2, S.T.v3, 'IT FIRES IN A CRASH'], [S.T.v3, S.T.v4, 'WHY SNUG MATTERS'], [S.T.v4, 15.3, 'THE FORCE LIMITER']];
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
  const rr = K.rng(3); c.globalCompositeOperation = 'screen'; t *= 3.4;      // slow drifting bokeh keeps the panel alive
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
function pauseIcon(c, t) {
  if (t < T_FREEZE || t > 5.5) return; const a = K.clamp((t - T_FREEZE) / .06, 0, 1) * K.clamp((5.5 - t) / .2, 0, 1);
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
  S.events = { impacts: IMP.map(i => ({ t: i.t, s: i.s })), whoosh: WHOOSH, stop: T_STOP, freeze: T_FREEZE, screech: [3.62, 4.08], reverse: 14.85,
    land: [.36, 1.00, 2.70, 16.62], scratch: T_FREEZE, resume: T_RESUME, T: S.T };
};
S.frame = (f, fps) => {
  const t = f / fps, cm = camAt(t), cp = camAt(t - 1 / fps);
  wx.setTransform(1, 0, 0, 1, 0, 0); wx.fillStyle = '#0d1424'; wx.fillRect(0, 0, K.W, K.H);
  wx.save(); K.apply(wx, cm); world(wx, t, cm); wx.restore();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const vx = (cm.x - cp.x) * cm.z, vy = (cm.y - cp.y) * cm.z, sp = Math.hypot(vx, vy), cut = cm.shot !== cp.shot;
  const frozen = t >= T_FREEZE && t < T_RESUME, sat = frozen ? (t < 4.75 ? .25 : .55) : 1;
  ctx.filter = sat < 1 ? `saturate(${sat}) brightness(.92)` : 'none';
  if (!cut && sp > 30) { const n = 8, L = Math.min(sp, 260); ctx.drawImage(wc, 0, 0); ctx.globalAlpha = .5; for (let k = 1; k < n; k++) ctx.drawImage(wc, -vx / sp * L * k / n, -vy / sp * L * k / n); ctx.globalAlpha = 1; }
  else ctx.drawImage(wc, 0, 0);
  ctx.filter = 'none';
  for (const im of IMP) { const k = Math.round((t - im.t) * fps);
    if (k === 0 && im.inv) { ctx.filter = 'grayscale(1) invert(1) contrast(3)'; ctx.drawImage(ctx.canvas, 0, 0); ctx.filter = 'none'; }
    const fl = k === 0 ? (im.inv ? .25 : .75) : k === 1 ? .55 : k === 2 ? .25 : k === 3 ? .1 : 0;
    if (fl > 0) { ctx.fillStyle = `rgba(255,248,232,${fl * im.fl})`; ctx.fillRect(0, 0, K.W, K.H); } }
  if (frozen) { ctx.fillStyle = 'rgba(40,90,140,.12)'; ctx.fillRect(0, 0, K.W, K.H); }
  post(ctx, f, { bloom: frozen ? .2 : .34 });
  pauseIcon(ctx, t); diagrams(ctx, t); limiterCard(ctx, t); headline(ctx, t); captions(ctx, t);
  if (t >= 16.66 && t < 17.5) K.poll(ctx, 160, 300, Math.min((t - 16.66) / .2, (17.5 - t) / .14), t > 17.0 ? 1 : 0);
  tag(ctx);
};
window.SCENE = S;
})();
