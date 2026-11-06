// Stage for the 3D-pixel car episodes: 360x640 tiles (pixpost.py reduces them to 180x320, then 6x), sand floor with a light pool and joints,
// slatted navy roller-door backdrop, orbit camera with lens shift, and the multi-pass ID render pixpost.py reads:
//   canvas 1440x640 = [info | depth | info without the car shell | depth without the shell]   (x-ray tiles optional)
import * as THREE from 'three';
import { ID, U, mat } from './toon.js';

export const SW = 360, SH = 640, K = 3;
export function stage(canvas) {
  canvas.width = SW * 4; canvas.height = SH;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(SW * 4, SH, false); renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.autoClear = false; renderer.setScissorTest(true);
  const scene = new THREE.Scene();
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), mat(ID.SAND, { kind: 1 })); floor.rotation.x = -Math.PI / 2; scene.add(floor);
  const back = new THREE.Mesh(new THREE.CylinderGeometry(15, 15, 9, 112, 1, true), mat(ID.BACK, { kind: 2, side: THREE.BackSide })); back.position.y = 4.5; scene.add(back);
  const camera = new THREE.PerspectiveCamera(34, SW / SH, 0.05, 80); scene.add(camera);

  // rig: target, yaw (deg; 0 = camera on +z, 90 = in front of the car), pitch (deg), dist, fov, shift (target's NDC drop)
  function shoot({ target = [0, 0.55, 0], yaw = 30, pitch = 12, dist = 11, fov = 34, shift = 0.5, roll = 0 }) {
    const y = THREE.MathUtils.degToRad(yaw), p = THREE.MathUtils.degToRad(pitch);
    camera.fov = fov; camera.position.set(target[0] + Math.sin(y) * Math.cos(p) * dist, target[1] + Math.sin(p) * dist, target[2] + Math.cos(y) * Math.cos(p) * dist);
    camera.up.set(Math.sin(THREE.MathUtils.degToRad(roll)), 1, 0).normalize(); camera.lookAt(...target);
    // lights follow the camera: warm key from the upper left of the frame, cool rim from behind-right
    const hx = Math.sin(y), hz = Math.cos(y), rx = Math.cos(y), rz = -Math.sin(y);
    U.uKey.value.set(hx * 0.7 - rx * 0.6, 0.85, hz * 0.7 - rz * 0.6).normalize();
    U.uRim.value.set(-hx * 0.8 + rx * 0.5, 0.35, -hz * 0.8 + rz * 0.5).normalize();
    camera.updateProjectionMatrix(); camera.projectionMatrix.elements[9] = shift;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert(); camera.updateMatrixWorld(true);
  }
  const v = new THREE.Vector3();
  function project(p) {                               // world point -> 1080x1920 px + on-screen flag
    v.copy(p).project(camera);
    return [Math.round((v.x + 1) / 2 * SW * K), Math.round((1 - v.y) / 2 * SH * K), v.z < 1 ? 1 : 0];
  }
  function tile(i, clear) {
    renderer.setViewport(i * SW, 0, SW, SH); renderer.setScissor(i * SW, 0, SW, SH);
    renderer.setClearColor(clear, 1); renderer.clear();
  }
  // shell: the object hidden for the x-ray tiles (or null)
  function render(shell, xray) {
    U.uNear.value = camera.near; U.uFar.value = 40;
    const pass = (i, mode) => { U.uMode.value = mode; tile(i, mode ? 0xffff00 : 0x000000); renderer.render(scene, camera); };
    pass(0, 0); pass(1, 1);
    if (xray && shell) { shell.visible = false; pass(2, 0); pass(3, 1); shell.visible = true; }
    else { tile(2, 0); tile(3, 0); }
  }
  return { renderer, scene, camera, floor, back, shoot, project, render };
}
