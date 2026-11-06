// rear-engine-3d: camera script + car poses. Rendered by shared/assets/pix3d/render3d.mjs (deterministic time steps).
// Shots (new view every 1-1.5 s):
//  0.0 orbit  1.0 rear 3/4  2.0 x-ray push  3.5 x-ray side  5.0 side launch  6.5 rear tyre  8.0 top-down corner
//  9.5 chase  11.0 wheel close-up  12.5 low rear  14.0 orbit (same rig as 0.0, so 16.0 == 0.0)
import * as THREE from 'three';
import { stage } from '../../../shared/assets/3d-car/stage.js';
import { ID, U, mat } from '../../../shared/assets/3d-car/toon.js';
import { buildCoupe, DIM } from '../../../shared/assets/3d-car/coupe.js';
import { buildGuy } from '../../../shared/assets/3d-car/presenter3d.js';

export const DUR = 16;
const ss = (a, b, x) => { const u = Math.min(1, Math.max(0, (x - a) / (b - a))); return u * u * (3 - 2 * u); };
const lerp = (a, b, u) => a + (b - a) * u;

export function build(canvas) {
  const S = stage(canvas), car = buildCoupe(THREE, mat), guy = buildGuy(THREE, mat);
  S.scene.add(car.group); S.camera.add(guy.group);
  // weight arrow (points down at the rear axle)
  const arrow = new THREE.Group(), am = mat(ID.ARROW, { spec: 0.4 });
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.5, 12), am); shaft.position.y = 0.45; arrow.add(shaft);
  const tip = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.26, 16), am); tip.rotation.x = Math.PI; tip.position.y = 0.1; arrow.add(tip);
  S.scene.add(arrow);
  // skid marks (top-down corner)
  const NSK = 160, skid = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.12, 0.16), mat(ID.SKID, { kind: 3, level: 0.6 }), NSK);
  S.scene.add(skid); const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), Y = new THREE.Vector3(0, 1, 0);

  // corner path (8-11 s): circle R around the origin, tail swinging out (slip angle beta)
  const R = 6.0, W0 = 0.8, PH0 = -0.6;
  const corner = (tau) => {
    const ph = PH0 + W0 * tau, pos = new THREE.Vector3(R * Math.cos(ph), 0, R * Math.sin(ph));
    const T = new THREE.Vector3(-Math.sin(ph), 0, Math.cos(ph)), inw = pos.clone().multiplyScalar(-1 / R);
    const beta = 0.46 * ss(0.25, 1.4, tau) + 0.1 * ss(1.4, 2.4, tau) - 0.2 * ss(2.5, 3.0, tau);
    const d = T.clone().multiplyScalar(Math.cos(beta)).addScaledVector(inw, Math.sin(beta)).normalize();
    return { pos, T, inw, beta, d, yaw: Math.atan2(-d.z, d.x), spin: R * W0 * tau / DIM.rR };
  };
  const rearPts = (c) => { const side = new THREE.Vector3(-c.d.z, 0, c.d.x); return [1, -1].map(s => c.pos.clone().addScaledVector(c.d, DIM.xR).addScaledVector(side, s * DIM.zR)); };

  function frame(t) {
    let rig, xray = 0, pose = { spin: 0 }, point = 'engine', carPos = new THREE.Vector3(), carYaw = 0, guyAt = [0.15, 0.985], shrug = 0;
    let floorOff = 0, backRot = 0, arrowOn = 0, skidOn = false;
    U.uTime.value = t;
    if (t < 1 || t >= 14) {                                      // fast orbit (loops: 16 s == 0 s)
      const tau = t < 1 ? t : t - 16;
      rig = { target: [-0.15, 0.5, 0], yaw: 35 - 82 * tau, pitch: 11 + 2 * tau, dist: 11.4 + 0.5 * tau, fov: 34, shiftX: 0.16 };
      point = t >= 14 ? null : 'engine'; shrug = ss(14.1, 14.4, t) * (1 - ss(15.6, 15.9, t));
    } else if (t < 2) {                                          // rear 3/4, low: tail, duck tail, exhausts
      const tau = t - 1; rig = { target: [-1.45, 0.6, 0], yaw: -132 + 30 * tau, pitch: 14, dist: 7.4 - 0.7 * tau, fov: 34 };
      point = 'tail'; guyAt = [0.14, 0.985];
    } else if (t < 3.5) {                                        // body turns x-ray, push in on the rear
      const tau = t - 2; xray = 0.6 * ss(0.05, 0.45, tau);
      rig = { target: [-1.0, 0.45, 0], yaw: -60 + 8 * tau, pitch: 32 - 4 * tau, dist: lerp(10, 7.2, ss(0, 1.5, tau)), fov: 34 };
      point = 'engine';
    } else if (t < 5) {                                          // x-ray side: engine sits behind the rear axle
      const tau = t - 3.5; xray = 0.6;
      rig = { target: [-1.3, 0.5, 0], yaw: 8 - 10 * tau, pitch: 10, dist: 6.6 - 0.5 * tau, fov: 34 };
      point = tau < 0.75 ? 'engine' : 'rear_axle';
    } else if (t < 8) {                                          // launch: squat, weight arrow, hot rear tyres
      const tau = t - 5, s = 1.5 * tau + 3.2 * tau * tau;
      floorOff = s; backRot = -s / 15; pose = { spin: s / DIM.rR, squat: 0.032 * ss(0, 0.5, tau) * (1 - 0.3 * ss(2.2, 3, tau)), hot: tau > 0.55 ? 1 : 0 };
      arrowOn = ss(0.15, 0.45, tau);
      if (t < 6.5) { rig = { target: [0, 0.55, 0], yaw: 180 + 4 * tau, pitch: 5, dist: 13.6, fov: 34, shiftX: 0.12 }; point = 'rear_tyre_l'; guyAt = [0.13, 0.985]; }
      else { const u = t - 6.5; rig = { target: [-1.25, 0.6, -0.55], yaw: -150 + 10 * u, pitch: 11, dist: 3.9 - 0.35 * u, fov: 34 }; point = 'rear_tyre_l'; }
    } else if (t < 11) {                                         // top-down corner, tail swings out
      const tau = t - 8, c = corner(tau);
      carPos = c.pos; carYaw = c.yaw; pose = { spin: c.spin, steer: -0.25 * ss(0, 0.5, tau) + 0.45 * ss(0.8, 1.6, tau) }; skidOn = true; point = 'tail';
      if (t < 9.5) { const c0 = corner(0); rig = { target: [c.pos.x, 0.3, c.pos.z], yaw: THREE.MathUtils.radToDeg(Math.atan2(-c0.T.x, -c0.T.z)) + 30, pitch: 84, dist: 17, fov: 34, shift: 0.28 }; }
      else { const off = c.T.clone().multiplyScalar(-0.75).addScaledVector(c.inw, -0.66); rig = { target: [c.pos.x, 0.4, c.pos.z], yaw: THREE.MathUtils.radToDeg(Math.atan2(off.x, off.z)), pitch: 56, dist: 10.5, fov: 34, shift: 0.32 }; }
    } else if (t < 12.5) {                                       // wheel + tyre close-up (wide rear tyre)
      const tau = t - 11; pose = { spin: 0.6 * tau };
      rig = { target: [-1.18, 0.38, 0.82], yaw: -24 + 9 * tau, pitch: 7, dist: 2.6 - 0.25 * tau, fov: 34, shift: 0.38 }; point = 'rear_tyre';
    } else {                                                     // low rear: wide rear stance + electronics chip
      const tau = t - 12.5; rig = { target: [-1.4, 0.5, 0], yaw: -100 + 14 * tau, pitch: 9, dist: 7.0 - 0.5 * tau, fov: 34, shiftX: 0.14 }; point = 'rear_tyre';
    }
    car.group.position.copy(carPos); car.group.rotation.y = carYaw;
    car.pose({ ...pose, xray: xray > 0, glowPulse: 0.12 + 0.1 * Math.sin(t * 9) });
    S.shoot(rig);
    U.uFloorOff.value.set(floorOff, 0); S.back.rotation.y = backRot;
    U.uPool.value.set(carPos.x, 0, carPos.z); U.uShadow.value.set(carPos.x, carPos.z, carYaw, 0.38);
    // arrow above the rear axle
    car.group.updateMatrixWorld(true);
    const ra = car.anchor('rear_axle'); arrow.visible = arrowOn > 0.01; arrow.scale.setScalar(arrowOn);
    arrow.position.set(ra.x, 1.25 + 0.12 * Math.abs(Math.sin(t * 5)), ra.z);
    // skid marks from the rear tyres
    let n = 0;
    if (skidOn) {
      const tau = t - 8;
      for (let k = 0; k < NSK / 2 && n < NSK; k++) {
        const tk = tau - k * 0.025; if (tk < 0) break;
        const c = corner(tk); if (c.beta < 0.12) continue;
        for (const p of rearPts(c)) { Q.setFromAxisAngle(Y, Math.atan2(-c.T.z, c.T.x) + Math.PI / 2); M.compose(p.setY(0.006), Q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2)), new THREE.Vector3(1, 1, 1)); skid.setMatrixAt(n++, M); }
      }
    }
    skid.count = n; skid.instanceMatrix.needsUpdate = true; skid.visible = n > 0;
    // presenter: lower-left, pointing at the part being discussed (screen space)
    guy.place(S.camera, guyAt[0], guyAt[1], 0.19);
    const pt = point ? S.project(car.anchor(point)) : null;
    guy.pose({ t, cam: S.camera, point: pt ? [pt[0] / 1080, pt[1] / 1920] : null, shrug, talk: 0 });
    S.render(car.shell, xray > 0);
    const out = { _x: xray };
    for (const nm of Object.keys(car.ANCHORS)) out[nm] = S.project(car.anchor(nm));
    out.arrow = S.project(arrow.position.clone().add(new THREE.Vector3(0, 0.8 * arrowOn, 0)));
    return out;
  }
  return { frame };
}
