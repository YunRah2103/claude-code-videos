// Generic low-poly cars (no logos, no badges): flat-shaded extruded profiles, 8-sided wheels.
// Car faces +z (front), length along z. car.userData: { wheels, tails, heads, flames, body } for animation.
import * as THREE from 'three';
import { P } from './palette.js';
import { mat } from './voxel.js';

const PROFILES = {
  // side profiles (u along length from rear to front, v up); lower body and greenhouse separately
  saloon: { body: [[-10, 1.6], [10, 1.6], [10.4, 4.6], [9, 5.6], [4.2, 6.0], [-6.8, 6.2], [-10, 5.6]],
            glass: [[3.8, 5.9], [1.4, 8.6], [-4.8, 8.6], [-7.2, 6.0]], roof: [[1.6, 8.5], [-4.9, 8.5]], w: 10, wb: 6.3 },
  sports: { body: [[-10, 1.4], [10.5, 1.4], [10.8, 3.4], [6, 4.8], [-5, 5.0], [-10, 4.6]],
            glass: [[5.2, 4.7], [1.6, 7.2], [-2.4, 7.2], [-8.8, 4.8]], roof: [[1.6, 7.1], [-2.6, 7.1]], w: 10.4, wb: 6.6 },
};

function extrude(pts, width, m) {
  const s = new THREE.Shape(pts.map(([u, v]) => new THREE.Vector2(u, v)));
  const geo = new THREE.ExtrudeGeometry(s, { depth: width, bevelEnabled: false, curveSegments: 1 });
  geo.translate(0, 0, -width / 2); geo.rotateY(-Math.PI / 2);            // length along z, front at +z
  return new THREE.Mesh(geo, m);
}

export function car(color, kind = 'saloon') {
  const pr = PROFILES[kind], g = new THREE.Group(), body = new THREE.Group(); g.add(body);
  const paint = new THREE.MeshLambertMaterial({ color, flatShading: true });
  body.add(extrude(pr.body, pr.w, paint));
  body.add(extrude(pr.glass, pr.w - 1.4, mat(P.glass)));
  const roof = new THREE.Mesh(new THREE.BoxGeometry(pr.w - 1.2, 0.6, pr.roof[0][0] - pr.roof[1][0]), paint);
  roof.position.set(0, pr.roof[0][1] + 0.1, (pr.roof[0][0] + pr.roof[1][0]) / 2); body.add(roof);
  const sill = new THREE.Mesh(new THREE.BoxGeometry(pr.w + 0.2, 0.8, 16), mat(P.silverSh)); sill.position.set(0, 1.9, 0); body.add(sill);
  const tails = [], heads = [], flames = [];
  for (const s of [-1, 1]) {
    const tl = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.9, 0.4), mat(P.tail, true)); tl.position.set(s * (pr.w / 2 - 1.6), 4.3, -10.1); body.add(tl); tails.push(tl);
    const hl = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.8, 0.4), mat(P.head, true)); hl.position.set(s * (pr.w / 2 - 1.6), kind === 'sports' ? 2.9 : 4.0, 10.3); body.add(hl); heads.push(hl);
    const fl = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 2.4), mat(P.flame, true)); fl.position.set(s * 2.2, 2.0, -11.4); fl.visible = false; body.add(fl); flames.push(fl);
  }
  const grille = new THREE.Mesh(new THREE.BoxGeometry(4.5, 1, 0.3), mat(P.navy)); grille.position.set(0, 3.0, 10.3); body.add(grille);
  const wheels = [];
  const tyreGeo = new THREE.CylinderGeometry(2.3, 2.3, 1.8, 8); tyreGeo.rotateZ(Math.PI / 2);
  const hubGeo = new THREE.CylinderGeometry(1.1, 1.1, 1.9, 6); hubGeo.rotateZ(Math.PI / 2);
  for (const z of [-pr.wb, pr.wb]) for (const s of [-1, 1]) {
    const w = new THREE.Group(); w.add(new THREE.Mesh(tyreGeo, mat(P.tyre))); w.add(new THREE.Mesh(hubGeo, mat(P.hub)));
    w.position.set(s * (pr.w / 2 - 0.6), 2.3, z); g.add(w); wheels.push(w);
  }
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(pr.w + 3, 22), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.45, depthWrite: false }));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.06; g.add(shadow);
  g.userData = { body, wheels, tails, heads, flames, kind };
  return g;
}

// Drive helper: place car at z (front axis), spin wheels by distance, body pitch/roll for launch, brake and rev shake.
export function poseCar(c, { x = 0, z = 0, dist = 0, pitch = 0, shake = 0, flame = false, brake = 0, t = 0, yaw = 0 }) {
  const u = c.userData; c.position.set(x, 0, z); c.rotation.y = yaw;
  u.wheels.forEach(w => { w.rotation.x = dist / 2.3; });
  u.body.rotation.x = -pitch; u.body.position.y = shake * Math.sin(t * 90) * 0.35; u.body.rotation.z = shake * Math.sin(t * 70) * 0.02;
  u.flames.forEach((f, i) => { f.visible = flame && ((Math.floor(t * 30) + i) % 3 !== 0); f.scale.z = 0.6 + ((Math.floor(t * 40) * 7 + i * 3) % 5) / 5; });
  u.tails.forEach(l => l.scale.set(1 + brake * 0.6, 1 + brake * 0.8, 1));
}
