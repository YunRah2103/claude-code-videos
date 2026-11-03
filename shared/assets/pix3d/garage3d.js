// Dark brick garage room with ceiling lamps and a fan of yellow light rays from the top (the 2D garage, in 3D).
import * as THREE from 'three';
import { P } from './palette.js';
import { pixTex, hex, mat } from './voxel.js';

export function brickTex(rx, ry) {
  return pixTex(32, 32, g => {
    g.fillStyle = hex(P.mortar); g.fillRect(0, 0, 32, 32);
    for (let row = 0; row < 8; row++) for (let col = 0; col < 5; col++) {
      const x = col * 8 - (row % 2) * 4, y = row * 4;
      g.fillStyle = hex((row * 3 + col * 7) % 5 === 0 ? P.brickB : P.brickA); g.fillRect(x + 1, y + 1, 7, 3);
      if ((row + col) % 3 === 0) { g.fillStyle = hex(P.wall); g.fillRect(x + 1, y + 1, 7, 1); }
    }
  }, [rx, ry]);
}
export function floorTex(rx, ry) {
  return pixTex(32, 32, g => {
    g.fillStyle = hex(P.floor); g.fillRect(0, 0, 32, 32);
    g.fillStyle = hex(P.floorLine); g.fillRect(0, 0, 32, 1); g.fillRect(0, 0, 1, 32); g.fillRect(0, 16, 32, 1); g.fillRect(16, 0, 1, 32);
    g.fillStyle = hex(0x1e2024); g.fillRect(5, 22, 4, 2); g.fillRect(22, 6, 3, 2);
  }, [rx, ry]);
}

// Room: x in [-hw, hw], z in [z0, z1], floor at y=0, ceiling at height. Returns { group, rays } (rays.rotation can drift).
export function garage({ hw = 150, z0 = -70, z1 = 200, height = 110, lamps = [[-40, -20], [40, -20], [0, 60]], raysAt = null, door = null } = {}) {
  const g = new THREE.Group();
  const wallMat = (w, h) => new THREE.MeshLambertMaterial({ map: brickTex(w / 16, h / 16), flatShading: true });
  const back = new THREE.Mesh(new THREE.PlaneGeometry(hw * 2, height), wallMat(hw * 2, height)); back.position.set(0, height / 2, z0); g.add(back);
  const front = back.clone(); front.rotation.y = Math.PI; front.position.z = z1; g.add(front);
  for (const s of [-1, 1]) {
    const side = new THREE.Mesh(new THREE.PlaneGeometry(z1 - z0, height), wallMat(z1 - z0, height));
    side.rotation.y = -s * Math.PI / 2; side.position.set(s * hw, height / 2, (z0 + z1) / 2); g.add(side);
  }
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(hw * 2, z1 - z0), new THREE.MeshLambertMaterial({ map: floorTex(hw / 16, (z1 - z0) / 16) }));
  floor.rotation.x = -Math.PI / 2; floor.position.set(0, 0, (z0 + z1) / 2); g.add(floor);
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(hw * 2, z1 - z0), mat(P.ceil)); ceil.rotation.x = Math.PI / 2;
  ceil.position.set(0, height, (z0 + z1) / 2); g.add(ceil);
  // ceiling lamps: a bright bar + an additive cone of light down to the floor
  const coneMat = new THREE.MeshBasicMaterial({ color: P.glowHi, transparent: true, opacity: 0.035, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  for (const [x, z] of lamps) {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(16, 1.5, 4), mat(P.light, true)); bar.position.set(x, height - 2, z); g.add(bar);
    const hood = new THREE.Mesh(new THREE.BoxGeometry(20, 2, 6), mat(P.silverSh)); hood.position.set(x, height - 0.5, z); g.add(hood);
    const cone = new THREE.Mesh(new THREE.CylinderGeometry(6, 34, height - 3, 8, 1, true), coneMat); cone.position.set(x, (height - 3) / 2, z); g.add(cone);
    const pool = new THREE.Mesh(new THREE.CircleGeometry(30, 10), new THREE.MeshBasicMaterial({ color: P.glow, transparent: true, opacity: 0.035, blending: THREE.AdditiveBlending, depthWrite: false }));
    pool.rotation.x = -Math.PI / 2; pool.position.set(x, 0.05, z); g.add(pool);
  }
  // fan of yellow rays spreading down from a point at the top of the back wall
  const rays = new THREE.Group(); rays.position.set(...(raysAt || [0, height + 6, z0 + 2]));
  const rayMat = new THREE.MeshBasicMaterial({ color: P.glow, transparent: true, opacity: 0.085, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  for (let i = 0; i < 9; i++) {
    const a = -1.15 + i * 2.3 / 8, len = 260, wid = 0.075;
    const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(Math.sin(a - wid) * len, -Math.cos(a - wid) * len, 0), new THREE.Vector3(Math.sin(a + wid) * len, -Math.cos(a + wid) * len, 0)]);
    rays.add(new THREE.Mesh(geo, rayMat));
  }
  g.add(rays);
  if (door) {                                           // open roller door in the back wall: [x, width, height]
    const [dx, dw, dh] = door;
    const hole = new THREE.Mesh(new THREE.PlaneGeometry(dw, dh), mat(0x050506)); hole.position.set(dx, dh / 2, z0 + 0.3); g.add(hole);
    for (let i = 0; i < 4; i++) { const slat = new THREE.Mesh(new THREE.BoxGeometry(dw + 2, 2, 1.5), mat(i % 2 ? P.silver : P.silverSh)); slat.position.set(dx, dh + 1 + i * 2, z0 + 0.8); g.add(slat); }
    for (const s of [-1, 1]) { const st = new THREE.Mesh(new THREE.BoxGeometry(1.5, dh + 8, 2), mat(P.glow)); st.position.set(dx + s * (dw / 2 + 1), (dh + 8) / 2, z0 + 1); g.add(st); }
  }
  return { group: g, rays, rayMat };
}

export function lights(scene) {
  scene.add(new THREE.HemisphereLight(0xb8c0d8, 0x202228, 0.9));
  const key = new THREE.DirectionalLight(0xfff2d0, 2.0); key.position.set(-40, 120, 80); scene.add(key);
  const rim = new THREE.DirectionalLight(0xffd23f, 0.8); rim.position.set(60, 60, -80); scene.add(rim);
  scene.fog = new THREE.Fog(0x0e0f12, 260, 520);
}
