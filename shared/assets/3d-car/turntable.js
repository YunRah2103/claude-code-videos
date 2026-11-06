// Car review turntable: one fixed view per whole second (t = 0..9), no text, no presenter.
//   node shared/assets/pix3d/render3d.mjs shared/assets/3d-car/turntable.js <dir> 1 --times 0,1,2,3,4,5,6,7,8,9
import * as THREE from 'three';
import { stage } from './stage.js';
import { U, mat } from './toon.js';
import { buildCoupe } from './coupe.js';
const VIEWS = [
  { target: [0, 0.55, 0], yaw: 40, pitch: 12, dist: 10.5 }, { target: [0, 0.6, 0], yaw: 0, pitch: 4, dist: 12.5 },
  { target: [0, 0.55, 0], yaw: -140, pitch: 14, dist: 10.5 }, { target: [-1.6, 0.6, 0], yaw: -90, pitch: 8, dist: 6.5 },
  { target: [1.6, 0.55, 0], yaw: 90, pitch: 8, dist: 6.5 }, { target: [0, 0.5, 0], yaw: 30, pitch: 82, dist: 14, shift: 0.15 },
  { target: [1.8, 0.62, 0.5], yaw: 55, pitch: 8, dist: 2.4, shift: 0.3 }, { target: [1.27, 0.35, 0.8], yaw: 15, pitch: 6, dist: 2.4, shift: 0.3 },
  { target: [0, 0.55, 0], yaw: 140, pitch: 22, dist: 10.5 }, { target: [-0.4, 0.75, 0.9], yaw: -30, pitch: 10, dist: 4.5, shift: 0.3 },
];
export function build(canvas) {
  const S = stage(canvas), car = buildCoupe(THREE, mat); S.scene.add(car.group);
  return { frame(t) {
    const v = VIEWS[Math.min(VIEWS.length - 1, Math.floor(t + 1e-6))];
    car.pose({ spin: 0.3 }); S.shoot({ fov: 34, shift: 0.35, ...v });
    U.uPool.value.set(0, 0, 0); U.uShadow.value.set(0, 0, 0, 0.38); S.render(car.shell, false); return {};
  } };
}
