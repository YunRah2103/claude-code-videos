// Stage: 270x480 WebGL renderer (no antialiasing), narrow-FOV perspective camera driven by an orbit rig with
// shake and push-in, plus project() so Python can pin sharp full-res labels and the 2D presenter to 3D points.
import * as THREE from 'three';
import { garage, lights } from './garage3d.js';

export const SW = 270, SH = 480;
export function stage(canvas, room = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(SW, SH, false); renderer.setClearColor(0x0e0f12);
  const scene = new THREE.Scene(); lights(scene);
  const room3 = garage(room); scene.add(room3.group);
  const camera = new THREE.PerspectiveCamera(30, SW / SH, 1, 1000);
  // rig: target, yaw (deg, 0 = camera on +z looking -z), pitch (deg), dist, fov, roll, shake (amplitude)
  function shoot({ target = [0, 20, 0], yaw = 0, pitch = 15, dist = 150, fov = 30, roll = 0, shake = 0, t = 0 }) {
    const y = THREE.MathUtils.degToRad(yaw), p = THREE.MathUtils.degToRad(pitch);
    const n = (k) => Math.sin(t * 61 * k + k) * 0.6 + Math.sin(t * 37 * k + 2 * k) * 0.4;    // deterministic shake noise
    const tx = target[0] + shake * n(1), ty = target[1] + shake * n(2) * 0.8, tz = target[2];
    camera.fov = fov; camera.updateProjectionMatrix();
    camera.position.set(tx + Math.sin(y) * Math.cos(p) * dist, ty + Math.sin(p) * dist, tz + Math.cos(y) * Math.cos(p) * dist);
    camera.up.set(Math.sin(THREE.MathUtils.degToRad(roll + shake * n(3) * 0.4)), 1, 0).normalize();
    camera.lookAt(tx, ty, tz);
  }
  const v = new THREE.Vector3();
  function project(p) {                                 // world point -> full-res (1080x1920) screen px + depth scale
    v.set(...p).project(camera);
    const d = camera.position.distanceTo(new THREE.Vector3(...p));
    return [Math.round((v.x + 1) / 2 * SW * 4 * 10) / 10, Math.round((1 - v.y) / 2 * SH * 4 * 10) / 10,
            Math.round(1000 / (d * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) ) / 1000];
  }
  return { renderer, scene, camera, room: room3, shoot, project, render: () => renderer.render(scene, camera) };
}
