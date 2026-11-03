// speed-limit-deal-3d: Three.js timeline (270x480, rendered by shared/assets/pix3d/render3d.mjs).
// Times follow words.json (faster-whisper on the shipped voiceover). frame(t) poses everything and returns anchors.
import * as THREE from 'three';
import { stage } from '../../../shared/assets/pix3d/stage.js';
import { P } from '../../../shared/assets/pix3d/palette.js';
import { car, poseCar } from '../../../shared/assets/pix3d/cars.js';
import { speedo, forceWall } from '../../../shared/assets/pix3d/speedo.js';
import { handshake, key, padlock } from '../../../shared/assets/pix3d/props.js';
import { mat } from '../../../shared/assets/pix3d/voxel.js';

const DUR = 14.1, END_T = 13.78;
const SLAM = 1.2, BUMP = 3.6, T2 = 4.3, STAMP = 6.96, T3 = 7.75, FILL0 = 7.85, FILL1 = 8.3, T4 = 10.3, ZIP = 10.4,
      T5 = 11.7, TURN = 12.25, OPEN = 12.46, T6 = 12.95, PRE = -0.4;   // PRE: cars already rolling before frame 0 (loop pre-roll)
const WALL_Z = -30, STOP = WALL_Z + 10.9, START = 48, LANES = [-24, 0, 24];
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, t0, d) => clamp((t - t0) / d);
const io = u => u < 0.5 ? 2 * u * u : 1 - ((-2 * u + 2) ** 2) / 2, oc = u => 1 - (1 - u) ** 3;
const ob = u => { const c = 1.70158; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2; };
const lerp = (a, b, u) => a + (b - a) * u;
const lerpRig = (a, b, u) => Object.fromEntries(Object.keys(a).map(k => [k, Array.isArray(a[k]) ? a[k].map((v, i) => lerp(v, b[k][i], u)) : lerp(a[k], b[k], u)]));

// camera rigs per beat (start, end) — each beat pushes in slowly
const RIG = {
  b1: [{ target: [14, 24, 24], yaw: 28, pitch: 10, dist: 320, fov: 30, roll: 5 }, { target: [0, 34, -24], yaw: 0, pitch: 16, dist: 185, fov: 30, roll: 0 }],
  b1m: [{ target: [0, 33, -20], yaw: 3, pitch: 16, dist: 200, fov: 30, roll: 0 }],
  b2: [{ target: [0, 34, -24], yaw: 22, pitch: 16, dist: 185, fov: 30, roll: -2 }, { target: [0, 34, -24], yaw: 16, pitch: 16, dist: 165, fov: 30, roll: -2 }],
  b3: [{ target: [-4, 30, -30], yaw: -5, pitch: 6, dist: 250, fov: 30, roll: 0 }, { target: [-4, 31, -30], yaw: -9, pitch: 6, dist: 225, fov: 30, roll: 0 }],
  b4: [{ target: [22, 26, -24], yaw: 42, pitch: 18, dist: 235, fov: 30, roll: 0 }, { target: [22, 26, -30], yaw: 36, pitch: 18, dist: 220, fov: 30, roll: 0 }],
  b5: [{ target: [0, 30, -30], yaw: -12, pitch: 10, dist: 175, fov: 30, roll: 0 }, { target: [0, 30, -30], yaw: -6, pitch: 10, dist: 150, fov: 30, roll: 0 }],
  b6: [{ target: [0, 42, -24], yaw: 8, pitch: 16, dist: 250, fov: 30, roll: 0 }, { target: [0, 42, -24], yaw: 3, pitch: 16, dist: 240, fov: 30, roll: 0 }],
};
const BEATS = [[-1, 'b1', T2], [T2, 'b2', T3], [T3, 'b3', T4], [T4, 'b4', T5], [T5, 'b5', T6], [T6, 'b6', END_T + 0.4]];
function rig(t) {
  let i = BEATS.findIndex(([s, , e]) => t >= s && t < e); if (i < 0) i = BEATS.length - 1;
  const [s, name, e] = BEATS[i], [a, b] = RIG[name];
  let r = name === 'b1' ? lerpRig(lerpRig(a, RIG.b1m[0], oc(prog(t, PRE, 1.4 - PRE))), b, io(prog(t, 1.4, e - 1.4)))   // fast push-in to the slam
                       : lerpRig(a, b, io(prog(t, Math.max(0, s), e - Math.max(0, s))));
  if (i > 0 && t < s + 0.32) {                           // swing in from the previous beat's end framing
    const prev = RIG[BEATS[i - 1][1]][1]; r = lerpRig(prev, r, io(prog(t, s, 0.32)));
  }
  return r;
}

export async function build(canvas) {
  const S = stage(canvas, { hw: 120, z0: -150, z1: 260, height: 130, lamps: [[-60, 20], [60, 20], [-60, -100], [60, -100]], raysAt: [0, 132, -145], door: [52, 46, 40] });
  const { scene } = S;
  // road: asphalt strip with dashed lane lines
  const road = new THREE.Mesh(new THREE.PlaneGeometry(116, 410), mat(P.asphalt)); road.rotation.x = -Math.PI / 2; road.position.set(0, 0.03, 55); scene.add(road);
  for (const x of [-12, 12, 40]) for (let z = 250; z > -150; z -= 16) {
    const d = new THREE.Mesh(new THREE.BoxGeometry(1, 0.2, 7), mat(P.laneLine)); d.position.set(x, 0.08, z); scene.add(d);
  }
  for (const x of [-57, 57]) { const e = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.2, 410), mat(P.glow)); e.position.set(x, 0.08, 55); scene.add(e); }
  // the speedometer wall: force-field barrier across the three lanes, dial on a gantry above it
  const wall = forceWall({ w: 74, h: 30 }); wall.group.position.z = WALL_Z; scene.add(wall.group);
  const dial = speedo({ r: 9, vmax: 200, limit: 155 }); dial.group.position.set(0, 43, WALL_Z - 2);   scene.add(dial.group);   // small gauge above the wall
  for (const s of [-1, 1]) { const leg = new THREE.Mesh(new THREE.BoxGeometry(2, 40, 2), mat(P.silverSh)); leg.position.set(s * 13, 20, WALL_Z - 3); scene.add(leg); }
  const cars = [car(P.carRed), car(P.carBlue), car(P.carSilver)];
  cars.forEach(c => scene.add(c));
  const porsche = car(P.carOrange, 'sports'); scene.add(porsche);
  const shake = new THREE.Group(); scene.add(shake);
  const hs = handshake(0.95); scene.add(hs);
  const k = key(0.9); scene.add(k);
  const lock = padlock(1.3); scene.add(lock);
  const hostShadow = new THREE.Mesh(new THREE.CircleGeometry(7, 10), new THREE.MeshBasicMaterial({ color: 0, transparent: true, opacity: 0.5, depthWrite: false }));
  hostShadow.rotation.x = -Math.PI / 2; scene.add(hostShadow);

  function frame(t0) {
    const t = t0 >= END_T ? t0 - DUR : t0;                 // loop: the end replays the cold-open pre-roll
    // ---- the three cars
    const run = prog(t, PRE, SLAM - PRE), hit = t - SLAM, bump = t - BUMP;
    let z, pitch = 0, shk = 0, flame = false, brake = 0, speed = 0;
    if (t < SLAM) { z = START - (START - STOP) * run * run; pitch = 0.07 * Math.sin(run * Math.PI) ; speed = run; flame = run < 0.6; shk = 0.4; }
    else { z = STOP + 3.5 * Math.exp(-hit * 6) * Math.abs(Math.sin(hit * 14)); pitch = -0.12 * Math.exp(-hit * 7) * Math.cos(hit * 18); brake = 1; }
    if (t > BUMP - 0.4 && t < BUMP + 1) {                  // second try: rev and nudge the wall
      shk = t < BUMP ? 1 : 0; flame = t < BUMP && t > BUMP - 0.35;
      z = STOP + (t < BUMP ? 0.8 * prog(t, BUMP - 0.4, 0.4) : 1.6 * Math.exp(-bump * 7) * Math.abs(Math.sin(bump * 16)));
      pitch = t < BUMP ? 0.03 : -0.06 * Math.exp(-bump * 7);
    }
    const unlocked = t >= OPEN + 0.25 && t < END_T;
    cars.forEach((c, i) => {
      let zi = z + (t < SLAM ? [0.6, 0, 1.2][i] * run : 0), xi = LANES[i];
      if (unlocked && i === 1) zi = STOP - 40 * oc(prog(t, OPEN + 0.25, 0.8)) - 8 * prog(t, OPEN + 0.25, 0.8);
      poseCar(c, { x: xi, z: zi, dist: START - zi, pitch: pitch * (1 + 0.15 * i), shake: shk, flame, brake, t: t + i * 0.13, yaw: Math.PI });
    });
    // ---- the speedometer wall
    let value = 0, fill = 0, glow = 0;
    if (t < T3) { value = t < SLAM ? 155 * run ** 1.4 : 155 + Math.sin(t * 50) * 1.2 * Math.exp(-hit * 1.5); fill = value; glow = t >= SLAM ? Math.exp(-hit * 2) * 0.8 + 0.2 : 0; }
    else { const u = io(prog(t, FILL0, FILL1 - FILL0)); value = 155 * u + (u >= 1 ? Math.sin(t * 40) * 0.8 : 0); fill = value; glow = t >= FILL1 ? 1 : 0.2; }
    dial.set({ value, fill, glow, limitOn: t >= SLAM - 0.05 || t >= T3, t });
    const shatter = t >= OPEN && t < END_T ? t - OPEN : -1;
    const lastHit = t >= ZIP && t < ZIP + 0.5 && t < T5 ? -1 : (t >= BUMP ? bump : (t >= SLAM ? hit : -1));
    wall.set({ hit: lastHit, at: 0, base: t < T2 ? 0.3 : 0.15, shatter, t });
    wall.group.visible = true;
    // ---- handshake (beat 2), padlock + key (beat 5), Porsche-like car (beat 4)
    const hsK = t >= T2 + 0.1 && t < T3 + 0.1 ? ob(prog(t, T2 + 0.1, 0.3)) * (1 - prog(t, T3 - 0.1, 0.2)) : 0;
    hs.visible = hsK > 0.01; hs.scale.setScalar(Math.max(0.01, hsK)); hs.position.set(0, 18 + 1.2 * Math.sin(t * 4), STOP - 4);
    hs.rotation.y = 0.35 * Math.sin(t * 2.2) + (t >= STAMP ? 0.2 * Math.exp(-(t - STAMP) * 6) * Math.sin((t - STAMP) * 40) : 0);
    const lockK = t >= T5 - 0.05 && t < OPEN + 0.9 ? ob(prog(t, T5 - 0.05, 0.25)) : 0;
    lock.visible = lockK > 0.01 && t < END_T; lock.scale.setScalar(Math.max(0.01, lockK));
    lock.position.set(0, Math.max(0, 16 - (t > OPEN + 0.15 ? 60 * (t - OPEN - 0.15) ** 2 : 0)), WALL_Z + 1);
    lock.rotation.z = t > OPEN + 0.15 ? -(t - OPEN - 0.15) * 3 : 0;
    lock.userData.shackle.position.y = 6 * 1.3 + (t > OPEN ? 3.5 * oc(prog(t, OPEN, 0.12)) : 0);
    const kIn = io(prog(t, T5 + 0.05, TURN - T5 - 0.05));
    k.visible = t >= T5 && t < OPEN + 0.5;
    k.position.set(lerp(26, 0, kIn), lerp(36, 16 + 3.5 * 1.3 - 3.5 * 0.9, kIn), lerp(70, WALL_Z + 2.6 + 9 - 4, kIn));
    k.rotation.set(0, Math.PI / 2 * (1 - kIn) + Math.PI / 2, (t > TURN ? Math.PI / 2 * io(prog(t, TURN, 0.15)) : 0) + 0.6 * (1 - kIn));
    const zu = prog(t, ZIP, 1.0);
    porsche.visible = t >= ZIP - 0.05 && t < T5;
    poseCar(porsche, { x: 48, z: lerp(70, -160, zu ** 1.1), dist: zu * 230, pitch: 0.02, t, yaw: Math.PI, flame: true });
    // ---- light rays drift, room lamps
    S.room.rays.rotation.z = 0.05 * Math.sin(t * 0.6) + (t < 1.5 ? 0.9 * (t - 1.5) : 0);   // fan sweeps in the cold open
    S.room.rayMat.opacity = (t < SLAM ? 0.11 : 0.075) + 0.02 * Math.sin(t * 1.7) + (t >= SLAM ? 0.08 * Math.exp(-hit * 3) : 0);
    // ---- camera: rig + shake (slam, bump, stamp) + punch-in on the stamp + loop swing back to the cold open
    const r = rig(t);
    let sh = (t < SLAM ? 1.6 : 0) + (t >= SLAM ? 5 * Math.exp(-hit * 4.5) : 0) + (t >= BUMP ? 2.2 * Math.exp(-bump * 6) : 0)
           + (t >= STAMP ? 3 * Math.exp(-(t - STAMP) * 7) : 0) + (t >= OPEN && t < END_T ? 2 * Math.exp(-(t - OPEN) * 6) : 0)
           + (t >= ZIP && t < T5 ? 1.2 * Math.exp(-((t - ZIP - 0.3) ** 2) * 20) : 0);
    if (t >= STAMP) r.dist -= 16 * Math.exp((STAMP - t) * 5) * (t < T3 ? 1 : 0);
    if (t >= SLAM && t < T2) r.dist -= 10 * Math.exp(-hit * 5);
    if (t0 >= END_T) {                                     // whip from the poll framing back to the cold-open start
      const u = io(prog(t0, END_T, 0.26)); const end = RIG.b6[1];
      const r0 = lerpRig(end, rig(t), u); Object.assign(r, r0); r.yaw += 38 * Math.sin(Math.PI * u);
    }
    S.shoot({ ...r, shake: sh, t });
    const hostX = -13, hostZ = WALL_Z - 5;            // stands just behind the force wall, between lanes
    hostShadow.position.set(hostX, 0.1, hostZ); hostShadow.visible = (t >= 2.1 && t < T3) || (t >= T6 && t < END_T);
    S.render();
    const A = {
      host: S.project([hostX, 0, hostZ]), carL: S.project([LANES[0], 12, STOP]), carM: S.project([LANES[1], 12, STOP]),
      carR: S.project([LANES[2], 12, STOP]), hand: S.project([0, 30, STOP - 4]), dial: S.project([0, 43, WALL_Z]),
      digits: S.project([0, 43 - 9 * 0.5, WALL_Z]), lock: S.project([0, 22, WALL_Z]), key: S.project([k.position.x, k.position.y, k.position.z]),
      porsche: S.project([48, 10, lerp(70, -160, zu ** 1.1)]), wall: S.project([0, 15, WALL_Z]),
    };
    return A;
  }
  return { frame };
}
