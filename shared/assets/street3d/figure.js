// Solid flat-shaded 3D limb figure (capsules + spheres), hand-posed. Pose fields (degrees):
// x,y,z (hip, metres; y is a lift above ground contact unless abs), face +1 (+X) / -1, lean (+ forward), head (+ nod),
// a1/a2 near arm (absolute shoulder angle from straight down, + forward; elbow bend), b1/b2 far arm, l1/l2 near leg
// (hip from down, knee bend: - = back), m1/m2 far leg, rot (whole-body roll about the hip, + = backflip),
// ya > 0 = absolute hip height; turn 0..1 (towards a camera on +Z of the parent; cz = -1 if the camera is on -Z), sx/sy squash, mouth 0..1, blink, brow, breathe.
import * as THREE from 'three';
const D = Math.PI / 180;
export const DIM = { torso: .5, neck: .07, head: .14, up: .3, fore: .28, thigh: .44, shin: .43 };
const mat = c => new THREE.MeshLambertMaterial({ color: c, flatShading: true });
const cap = (r, len, m) => { const g = new THREE.CapsuleGeometry(r, len, 3, 8); g.translate(0, -len / 2, 0); return new THREE.Mesh(g, m); };
const ball = (r, m, d = 2) => new THREE.Mesh(new THREE.IcosahedronGeometry(r, d), m);
export function makeFigure(kind = 'guy') {
  const G = kind === 'guy';
  const C = G ? { skin: '#8d5a3b', tee: '#f2efe8', shorts: '#17181d', hair: '#17120f', shoe: '#f4f4f0', sole: '#121318' }
              : { skin: '#7c1a1d', tee: '#7c1a1d', shorts: '#651418', hair: '#5c1215', shoe: '#5a1215', sole: '#3a0b0d' };
  const M = {}; for (const k in C) M[k] = mat(C[k]);
  const root = new THREE.Group(), pivot = new THREE.Group(); root.add(pivot);
  const spine = new THREE.Group(); pivot.add(spine);
  const hips = ball(.15, M.shorts); hips.scale.set(.9, .75, 1.25); pivot.add(hips);
  const torso = cap(.14, DIM.torso - .14, M.tee); torso.rotation.z = Math.PI; torso.position.y = .07; torso.scale.set(.85, 1, 1.4); spine.add(torso);
  const chest = new THREE.Group(); chest.position.y = DIM.torso; spine.add(chest);
  const neck = cap(.05, .08, M.skin); neck.rotation.z = Math.PI; chest.add(neck);
  const headG = new THREE.Group(); headG.position.y = DIM.neck + DIM.head; chest.add(headG);
  const head = ball(DIM.head, M.skin, 3); headG.add(head);
  const face = new THREE.Group(); headG.add(face);
  let mouth, eyes = [], brows = [];
  if (G) {
    const hair = ball(DIM.head * 1.08, M.hair, 2); hair.scale.set(1, .62, 1.02); hair.position.set(-.02, .055, 0); headG.add(hair);
    const back = ball(DIM.head * 1.0, M.hair, 2); back.scale.set(.75, .9, .98); back.position.set(-.05, .0, 0); headG.add(back);
    for (let i = 0; i < 7; i++) { const t = ball(.045, M.hair, 1); const a = i / 6 * Math.PI - Math.PI / 2; t.position.set(.06 * Math.cos(i * 1.7) - .02, .13 + .02 * Math.sin(i * 2.3), Math.sin(a) * .1); headG.add(t); }
    const fr = ball(.05, M.hair, 1); fr.scale.set(1.3, .6, 2.4); fr.position.set(.1, .085, .02); headG.add(fr);
    for (const s of [-1, 1]) { const ear = ball(.035, M.skin, 1); ear.position.set(-.01, -.01, s * .138); headG.add(ear); }
    const gm = new THREE.MeshLambertMaterial({ color: '#9aa3ad' }), em = new THREE.MeshBasicMaterial({ color: '#120d0b' });
    for (const s of [-1, 1]) {
      const ring = new THREE.Mesh(new THREE.RingGeometry(.04, .052, 4, 1), gm); ring.rotation.set(0, Math.PI / 2, Math.PI / 4); ring.position.set(.142, .012, s * .056); face.add(ring);
      const eye = ball(.016, em, 1); eye.scale.set(.6, 1.4, 1); eye.position.set(.132, .012, s * .056); face.add(eye); eyes.push(eye);
      const brow = new THREE.Mesh(new THREE.BoxGeometry(.012, .012, .055), M.hair); brow.position.set(.135, .07, s * .056); face.add(brow); brows.push(brow);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(.13, .01, .01), gm); arm.position.set(.08, .02, s * .108); face.add(arm);
      const ck = ball(.022, new THREE.MeshLambertMaterial({ color: '#b56a5a' }), 1); ck.scale.set(.4, .6, 1); ck.position.set(.12, -.04, s * .075); face.add(ck);
    }
    const bridge = new THREE.Mesh(new THREE.BoxGeometry(.01, .01, .03), gm); bridge.position.set(.145, .02, 0); face.add(bridge);
    mouth = ball(.03, new THREE.MeshBasicMaterial({ color: '#3a1410' }), 1); mouth.position.set(.128, -.07, 0); face.add(mouth);
  }
  const limb = (parent, pos, upR, loR, upLen, loLen, upM, loM, sleeve) => {
    const j = new THREE.Group(); j.position.set(...pos); parent.add(j);
    j.add(cap(upR, upLen, upM));
    if (sleeve) { const sl = cap(upR * 1.45, upLen * .38, sleeve); j.add(sl); }
    const k = new THREE.Group(); k.position.y = -upLen; j.add(k); k.add(cap(loR, loLen, loM));
    const e = new THREE.Group(); e.position.y = -loLen; k.add(e);
    return { j, k, e };
  };
  const armN = limb(chest, [0, -.05, .2], .052, .047, DIM.up, DIM.fore, M.skin, M.skin, M.tee);
  const armF = limb(chest, [0, -.05, -.2], .052, .047, DIM.up, DIM.fore, M.skin, M.skin, M.tee);
  for (const a of [armN, armF]) { const h = ball(.062, M.skin, 1); a.e.add(h); a.hand = h; }
  const legN = limb(pivot, [0, -.02, .1], .088, .062, DIM.thigh, DIM.shin, M.shorts, M.skin);
  const legF = limb(pivot, [0, -.02, -.1], .088, .062, DIM.thigh, DIM.shin, M.shorts, M.skin);
  for (const l of [legN, legF]) { const f = new THREE.Group(); l.e.add(f); l.foot = f;
    const sh = new THREE.Mesh(new THREE.BoxGeometry(.27, .09, .11), M.shoe); sh.position.set(.06, -.03, 0); f.add(sh);
    const so = new THREE.Mesh(new THREE.BoxGeometry(.28, .03, .115), M.sole); so.position.set(.06, -.085, 0); f.add(so); }
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(.45, 24), new THREE.MeshBasicMaterial({ color: '#0a0814', transparent: true, opacity: .45, depthWrite: false }));
  shadow.rotation.x = -Math.PI / 2;
  const fig = { root, shadow, kind, parts: { pivot, spine, chest, headG, armN, armF, legN, legF } };
  fig.set = (p) => {
    const f = p.face || 1, tu = p.turn || 0, cz = p.cz || 1;
    root.position.set(p.x || 0, 0, p.z || 0);
    root.rotation.set(0, (f > 0 ? 0 : Math.PI) - f * cz * tu * .45 * Math.PI / 2 + (p.yaw || 0) * D, 0);
    pivot.rotation.z = -(p.rot || 0) * D; pivot.scale.set(p.sx || 1, p.sy || 1, 1);
    const ln = p.lean || 0, br = Math.sin((p.breathe || 0)) * .015;
    spine.rotation.z = -ln * D; torso.scale.set(.85 + br, 1, 1.4 + br * 2);
    headG.rotation.set(0, -f * cz * tu * .55 * Math.PI / 2, -(p.head || 0) * D);
    armN.j.rotation.z = ((p.a1 || 0) + ln) * D; armN.k.rotation.z = (p.a2 || 0) * D;
    armF.j.rotation.z = ((p.b1 || 0) + ln) * D; armF.k.rotation.z = (p.b2 || 0) * D;
    armN.j.rotation.x = (p.ax || 0) * D; armF.j.rotation.x = -(p.bx || 0) * D;
    legN.j.rotation.z = (p.l1 || 0) * D; legN.k.rotation.z = (p.l2 || 0) * D; legN.foot.rotation.z = -((p.l1 || 0) + (p.l2 || 0)) * D * .85;
    legF.j.rotation.z = (p.m1 || 0) * D; legF.k.rotation.z = (p.m2 || 0) * D; legF.foot.rotation.z = -((p.m1 || 0) + (p.m2 || 0)) * D * .85;
    if (mouth) { const m = Math.max(0, Math.min(1, p.mouth || 0)); mouth.scale.set(.5, .35 + m * 1.3, 1.1 + m * .3);
      for (const e of eyes) e.scale.y = p.blink ? .2 : 1.4; brows.forEach(b => b.position.y = .07 + (p.brow || 0) * .015); }
    // ground contact: lowest sole on y = 0 unless abs
    root.updateMatrixWorld(true);
    let y;
    if (p.abs) y = p.y || 0;
    else if (p.ya > 0) y = p.ya;   // absolute hip height (flights, dives)
    else { const v = new THREE.Vector3(); let low = 1e9; for (const l of [legN, legF]) { l.foot.children[1].getWorldPosition(v); low = Math.min(low, v.y - .015); } y = -low + (p.y || 0); }
    root.position.y = y; shadow.position.set(p.x || 0, .012, p.z || 0); const h = Math.max(0, y - .9);
    shadow.scale.setScalar(Math.max(.3, 1 - h * .4)); shadow.material.opacity = .45 * Math.max(0, 1 - h * .5);
    root.updateMatrixWorld(true);
  };
  fig.hand = (near = true) => { const v = new THREE.Vector3(); (near ? armN : armF).hand.getWorldPosition(v); return v; };
  fig.headPos = () => { const v = new THREE.Vector3(); headG.getWorldPosition(v); return v; };
  fig.chestPos = () => { const v = new THREE.Vector3(); chest.getWorldPosition(v); return v; };
  return fig;
}
