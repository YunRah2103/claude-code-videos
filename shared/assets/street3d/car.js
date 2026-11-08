// Generic unbadged hatchback (metres, faces local +X, ground at y=0). Blank plate, no logos.
// `side` (+1/-1) is the local z side of the driver seat and the removable door (cutaway).
// API: car.group, car.setCrush(0..1), car.setDoor(open 0..1 | 'cut'), car.setAirbag(0..1), car.belt(points[], glow), car.spin(a)
import * as THREE from 'three';
const lam = (c, o = {}) => new THREE.MeshLambertMaterial(Object.assign({ color: c, flatShading: true }, o));
const box = (w, h, d, m, x, y, z) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); b.position.set(x, y, z); return b; };
export function makeCar(o = {}) {
  const s = o.side || -1, g = new THREE.Group(), paint = lam(o.color || '#2a8fa8'), dark = lam('#1d2030'), trim = lam('#3a3f52');
  const glass = new THREE.MeshLambertMaterial({ color: '#7cc4e0', transparent: true, opacity: .32, depthWrite: false, side: THREE.DoubleSide });
  const W = 1.8, hw = W / 2;
  const front = new THREE.Group(); front.position.set(1.05, 0, 0); g.add(front);                         // crumple zone
  front.add(box(1.05, .55, W, paint, .52, .62, 0)); front.add(box(1.0, .08, W * .96, paint, .45, .93, 0)); // engine block + bonnet
  front.add(box(.12, .22, W * .9, trim, 1.06, .42, 0));                                                  // bumper
  for (const z of [-1, 1]) { const hl = box(.06, .1, .32, new THREE.MeshBasicMaterial({ color: '#fff3c9' }), 1.05, .72, z * .6); front.add(hl); }
  front.add(box(.04, .12, .4, lam('#e8e4da'), 1.11, .44, 0));                                             // blank plate
  g.add(box(1.0, .62, W, paint, -1.55, .6, 0));                                                          // rear block
  g.add(box(.1, .2, W * .9, trim, -2.08, .42, 0));
  for (const z of [-1, 1]) g.add(box(.05, .14, .3, new THREE.MeshBasicMaterial({ color: '#ff3048' }), -2.06, .78, z * .62));
  g.add(box(.05, .12, .4, lam('#e8e4da'), -2.1, .5, 0));
  g.add(box(2.1, .1, W, dark, 0, .27, 0));                                                               // floor
  g.add(box(2.1, .62, .08, paint, 0, .6, -s * (hw - .04)));                                              // far door panel
  const door = box(2.1, .62, .08, paint, 0, .6, s * (hw - .04)); g.add(door);                            // near door (cut away)
  const sill = box(2.1, .14, .1, paint, 0, .3, s * (hw - .05)); g.add(sill);
  // roof, pillars, glass
  const roof = box(1.55, .07, W * .92, paint, -.35, 1.46, 0); g.add(roof);
  const pillar = (x0, y0, x1, y1, z) => { const len = Math.hypot(x1 - x0, y1 - y0), p = box(len, .08, .08, paint, (x0 + x1) / 2, (y0 + y1) / 2, z); p.rotation.z = Math.atan2(y1 - y0, x1 - x0); return p; };
  let bNear = null; for (const z of [-1, 1]) { g.add(pillar(1.0, .93, .42, 1.46, z * hw * .9)); g.add(pillar(-1.12, 1.46, -1.95, .9, z * hw * .9)); const bp = box(.09, .55, .08, paint, -.25, 1.2, z * hw * .9); g.add(bp); if (z === s) bNear = bp; }
  const ws = new THREE.Mesh(new THREE.PlaneGeometry(.8, W * .86), glass); ws.position.set(.71, 1.2, 0); ws.rotation.set(0, Math.PI / 2, 0); ws.rotateX(0); ws.rotation.z = 0;
  ws.rotation.set(-Math.PI / 2, -0.83, -Math.PI / 2); g.add(ws);
  const sideGlass = z => { const sh = new THREE.Shape(); sh.moveTo(.95, .95); sh.lineTo(.42, 1.42); sh.lineTo(-1.1, 1.42); sh.lineTo(-1.9, .95); sh.closePath();
    const m = new THREE.Mesh(new THREE.ShapeGeometry(sh), glass); m.position.z = z; return m; };
  const farGlass = sideGlass(-s * hw * .9); g.add(farGlass); const nearGlass = sideGlass(s * hw * .92); g.add(nearGlass);
  // wheels
  const wheels = [];
  for (const x of [1.35, -1.38]) for (const z of [-1, 1]) { const w = new THREE.Group(); w.position.set(x, .34, z * .82);
    const t = new THREE.Mesh(new THREE.CylinderGeometry(.34, .34, .24, 18), lam('#14151b')); t.rotation.x = Math.PI / 2; w.add(t);
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(.19, .19, .25, 6), lam('#c4c8d2')); hub.rotation.x = Math.PI / 2; w.add(hub);
    if (x > 0) front.attach(w); else g.add(w); wheels.push(w); }
  // interior: driver seat, wheel, dash, retractor
  const seat = new THREE.Group(); seat.position.set(-.25, 0, s * .42); g.add(seat);
  seat.add(box(.55, .14, .5, lam('#34406c'), 0, .45, 0)); const back = box(.14, .7, .5, lam('#3d4b7d'), -.3, .82, 0); back.rotation.z = .2; seat.add(back);
  seat.add(box(.16, .16, .36, lam('#3d4b7d'), -.4, 1.24, 0));
  const dash = box(.4, .3, W * .9, dark, .75, .85, 0); g.add(dash);
  const wheelG = new THREE.Group(); wheelG.position.set(.42, 1.0, s * .42); wheelG.rotation.z = .5; g.add(wheelG);
  const sw = new THREE.Mesh(new THREE.TorusGeometry(.17, .025, 6, 18), dark); sw.rotation.y = Math.PI / 2; wheelG.add(sw);
  const col = box(.3, .05, .05, dark, .15, -.05, 0); wheelG.add(col);
  const retr = box(.12, .16, .1, lam('#8a90a0'), -.3, .42, s * .8); g.add(retr);
  const dring = box(.06, .07, .05, lam('#c9ced8'), -.3, 1.24, s * .8); g.add(dring);
  const airbag = new THREE.Mesh(new THREE.IcosahedronGeometry(.3, 2), lam('#f1ede4')); airbag.position.set(.3, 1.05, s * .42); airbag.scale.setScalar(.001); g.add(airbag);
  const beltMat = new THREE.MeshLambertMaterial({ color: '#ffb347', emissive: '#ff9a2a', emissiveIntensity: .15 });
  let beltMesh = null;
  const car = { group: g, front, door, nearGlass, wheels, dring: dring.position.clone(), retr: retr.position.clone(), seatPos: seat.position, wheelPos: wheelG.position, side: s,
    setCrush(c) { front.scale.x = 1 - .38 * c; front.position.x = 1.05; front.rotation.z = -.06 * c; },
    setDoor(cut, roofOff = cut) { door.visible = !cut; nearGlass.visible = !cut; bNear.visible = !cut; roof.visible = !roofOff; },   // x-ray cutaway: near door, B-pillar (and roof) off
    setAirbag(u) { const k = Math.max(.001, u); airbag.scale.set(k * .9, k * 1.1, k * 1.05); airbag.position.x = .32 - .2 * u; },
    spin(a) { for (const w of wheels) w.rotation.z = -a; },
    belt(pts, glow) { if (beltMesh) { g.remove(beltMesh); beltMesh.geometry.dispose(); }
      const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal'); beltMesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 40, .028, 5, false), beltMat);
      beltMesh.scale.z = 1; beltMat.emissiveIntensity = .15 + glow * .9; g.add(beltMesh); },
  };
  return car;
}
