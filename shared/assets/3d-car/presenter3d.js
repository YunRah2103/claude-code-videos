// The main guy (characters/main-guy: dark hair, silver round-square glasses, white tee, dark jeans, white sneakers)
// rebuilt as a chunky 3D toon figure, so he goes through the same palette / dither / outline pass as the car.
//   const guy = buildGuy(THREE, mat); camera.add(guy.group);
//   guy.place(camera, sx, sy, heightFrac)        // pin to the screen (sx, sy in 0..1 from top-left, feet point)
//   guy.pose({ t, point: [sx, sy] | null, shrug: 0..1, talk: 0..1 })   // right arm aims at a screen point
// 1 unit = his height. Built facing +z (toward the camera when parented to it).
import { ID } from './toon.js';
import { RoundedBoxGeometry } from '../vendor/jsm/geometries/RoundedBoxGeometry.js';

export function buildGuy(THREE, mat) {
  const R = (w, h, d, r, id, o = {}) => new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 3, r), mat(id, o));
  const group = new THREE.Group(), root = new THREE.Group(); group.add(root);
  const legs = [], arms = {};
  for (const s of [1, -1]) {
    const leg = new THREE.Group(); leg.position.set(s * 0.075, 0.42, 0); root.add(leg);
    const jean = R(0.13, 0.36, 0.14, 0.04, ID.JEANS); jean.position.y = -0.2; leg.add(jean);
    const shoe = R(0.15, 0.08, 0.22, 0.035, ID.SHIRT, { spec: 0.3 }); shoe.position.set(0, -0.385, 0.03); leg.add(shoe);
    const sole = R(0.155, 0.025, 0.225, 0.01, ID.METAL); sole.position.set(0, -0.415, 0.03); leg.add(sole);
    legs.push(leg);
  }
  const belt = R(0.3, 0.05, 0.17, 0.02, ID.HAIR); belt.position.y = 0.43; root.add(belt);
  const torso = R(0.32, 0.27, 0.18, 0.06, ID.SHIRT, { spec: 0.15 }); torso.position.y = 0.58; root.add(torso);
  const neck = R(0.08, 0.05, 0.08, 0.02, ID.SKIN); neck.position.y = 0.73; root.add(neck);
  for (const s of [1, -1]) {                          // shoulder pivot -> sleeve + forearm + hand
    const sh = new THREE.Group(); sh.position.set(s * 0.19, 0.68, 0); root.add(sh);
    const sleeve = R(0.1, 0.12, 0.12, 0.04, ID.SHIRT, { spec: 0.15 }); sleeve.position.y = -0.05; sh.add(sleeve);
    const arm = R(0.07, 0.19, 0.07, 0.03, ID.SKIN); arm.position.y = -0.17; sh.add(arm);
    const hand = R(0.08, 0.07, 0.08, 0.03, ID.SKIN); hand.position.y = -0.28; sh.add(hand);
    const finger = R(0.03, 0.09, 0.03, 0.012, ID.SKIN); finger.position.set(0, -0.33, 0.01); finger.visible = s > 0; sh.add(finger);
    arms[s > 0 ? 'r' : 'l'] = sh;
  }
  const head = new THREE.Group(); head.position.y = 0.74; head.scale.setScalar(1.3); root.add(head);   // chibi head reads at 135x240
  const skull = R(0.3, 0.28, 0.26, 0.09, ID.SKIN, { spec: 0.1 }); skull.position.y = 0.13; head.add(skull);
  for (const s of [1, -1]) { const ear = R(0.04, 0.07, 0.05, 0.015, ID.SKIN); ear.position.set(s * 0.155, 0.12, -0.01); head.add(ear); }
  const hair = R(0.33, 0.13, 0.29, 0.06, ID.HAIR, { spec: 0.5 }); hair.position.set(0, 0.255, -0.01); head.add(hair);
  const quiff = R(0.14, 0.07, 0.12, 0.03, ID.HAIR, { spec: 0.6 }); quiff.position.set(0.05, 0.32, 0.06); quiff.rotation.z = -0.25; head.add(quiff);
  for (const s of [1, -1]) { const side = R(0.035, 0.1, 0.2, 0.015, ID.HAIR); side.position.set(s * 0.16, 0.19, -0.02); head.add(side); }
  const back = R(0.31, 0.2, 0.08, 0.04, ID.HAIR); back.position.set(0, 0.17, -0.11); head.add(back);
  const fringe = R(0.2, 0.04, 0.05, 0.02, ID.HAIR); fringe.position.set(-0.04, 0.235, 0.12); fringe.rotation.z = 0.12; head.add(fringe);
  for (const s of [1, -1]) {                          // glasses: square rims on a bridge, dark eyes behind
    const rim = new THREE.Mesh(new THREE.TorusGeometry(0.056, 0.017, 4, 4), mat(ID.SPECS, { spec: 0.9 }));
    rim.rotation.z = Math.PI / 4; rim.scale.set(1.15, 1.0, 1); rim.position.set(s * 0.07, 0.13, 0.135); head.add(rim);
    const eye = R(0.032, 0.045, 0.01, 0.008, ID.EYE); eye.position.set(s * 0.065, 0.125, 0.131); head.add(eye);
    const arm2 = R(0.012, 0.016, 0.14, 0.004, ID.SPECS); arm2.position.set(s * 0.15, 0.15, 0.07); head.add(arm2);
  }
  const bridge = R(0.04, 0.016, 0.012, 0.004, ID.SPECS); bridge.position.set(0, 0.145, 0.138); head.add(bridge);
  const mouth = R(0.07, 0.016, 0.01, 0.006, ID.TAIL); mouth.position.set(0, 0.045, 0.131); head.add(mouth);

  const v = new THREE.Vector3();
  // pin the feet to screen point (sx, sy) at a fixed distance in front of the camera; height = frac of the frame
  function place(cam, sx, sy, frac, dist = 1.0) {
    const th = Math.tan(cam.fov * Math.PI / 360) * dist * 2, tw = th * cam.aspect;
    const sh = cam.projectionMatrix.elements[9], sx2 = cam.projectionMatrix.elements[8];   // lens shift used by the episode camera
    group.position.set((sx - 0.5) * tw + sx2 * tw / 2, (0.5 - sy) * th + sh * th / 2, -dist);
    group.scale.setScalar(frac * th); group.rotation.set(0, 0.35, 0);
  }
  function pose({ t = 0, point = null, shrug = 0, talk = 0, cam = null } = {}) {
    root.position.y = 0.006 * Math.sin(t * 6); head.rotation.z = 0.05 * Math.sin(t * 2.3);
    head.rotation.y = 0.15 * Math.sin(t * 1.1); mouth.scale.y = 1 + 2.5 * talk * (0.5 + 0.5 * Math.sin(t * 22));
    let ar = -0.15, al = 0.15;                        // arms down (z rotation, + raises the left arm outward)
    if (point && cam) {                               // aim the right arm at the screen point (camera plane)
      group.updateMatrixWorld(true); v.set(0, 0, 0); arms.r.localToWorld(v); v.project(cam);
      const dx = (point[0] * 2 - 1) - v.x, dy = (1 - point[1] * 2) - v.y;
      ar = Math.atan2(dy * 16 / 9, dx) + Math.PI / 2;
    }
    if (shrug > 0) { ar = ar * (1 - shrug) + 1.2 * shrug; al = al * (1 - shrug) - 1.2 * shrug; }
    arms.r.rotation.z = ar; arms.l.rotation.z = al + 0.04 * Math.sin(t * 3);
    arms.r.rotation.x = 0; arms.r.children[3].visible = !shrug;
  }
  return { group, place, pose, head, arms };
}
