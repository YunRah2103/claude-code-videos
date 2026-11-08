// Stage: WebGL renderer (offscreen) + 2D compositor at 1080x1920.
// Depth of field: layer 1 (far city) is rendered on its own and blurred, layer 0 (street, cars, figures) sharp on top.
// Motion blur: N sub-frames per output frame across a 180-degree shutter, averaged. Post: vignette, fixed grain.
import * as THREE from 'three';
export function makeStage(canvas, o = {}) {
  const W = 1080, H = 1920, ctx = canvas.getContext('2d');
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setSize(W, H, false); renderer.setPixelRatio(1); renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(38, W / H, .05, 400);
  const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
  const farC = mk(), fx = farC.getContext('2d'), sub = mk(), sx = sub.getContext('2d');
  const vig = mk(), vx = vig.getContext('2d'); { const g = vx.createRadialGradient(W / 2, H * .5, H * .3, W / 2, H * .5, H * .75); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(6,4,18,.55)'); vx.fillStyle = g; vx.fillRect(0, 0, W, H); }
  const grain = document.createElement('canvas'); grain.width = 540; grain.height = 960; { const gx = grain.getContext('2d'), im = gx.createImageData(540, 960); let s = 7;
    for (let i = 0; i < im.data.length; i += 4) { s = (s * 1664525 + 1013904223) >>> 0; const v = 128 + ((s / 4294967296) - .5) * 90; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } gx.putImageData(im, 0, 0); }
  const N = o.subframes || 4, shutter = o.shutter ?? .5;
  // pose(tSub) sets the whole scene + camera for time tSub and returns { blur }
  let litAll = false;
  function frame(t, fps, pose) {
    let blur = 4;
    if (!litAll) { scene.traverse(o => { if (o.isLight) o.layers.enableAll(); }); litAll = true; }   // lights must reach both layers
    for (let k = 0; k < N; k++) {
      const ts = t + ((k + .5) / N - .5) * shutter / fps;
      const r = pose(ts) || {}; blur = r.blur ?? blur;
      if (k === 0) {   // far layer once per frame, blurred (it is soft anyway)
        camera.layers.set(1); renderer.setClearColor(0x000000, 0); renderer.render(scene, camera);
        fx.clearRect(0, 0, W, H); fx.filter = `blur(${blur}px)`; fx.drawImage(renderer.domElement, 0, 0); fx.filter = 'none';
      }
      const bg = scene.background; scene.background = null; camera.layers.set(0); renderer.setClearColor(0x000000, 0); renderer.render(scene, camera); scene.background = bg;
      sx.globalAlpha = 1; sx.drawImage(farC, 0, 0); sx.drawImage(renderer.domElement, 0, 0);
      ctx.globalAlpha = 1 / (k + 1); ctx.drawImage(sub, 0, 0);
    }
    ctx.globalAlpha = 1;
  }
  function post(flash = 0) {
    ctx.drawImage(vig, 0, 0);
    ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .05; ctx.drawImage(grain, 0, 0, W, H); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
    if (flash > 0) { ctx.fillStyle = `rgba(255,246,228,${flash})`; ctx.fillRect(0, 0, W, H); }
  }
  // spherical camera rig: tgt, dist, az (deg from +Z towards +X), el (deg), fov, roll
  function aim(c) { const D = Math.PI / 180, ce = Math.cos(c.el * D);
    camera.position.set(c.tx + c.dist * Math.sin(c.az * D) * ce, c.ty + c.dist * Math.sin(c.el * D), c.tz + c.dist * Math.cos(c.az * D) * ce);
    camera.up.set(Math.sin((c.roll || 0) * D), Math.cos((c.roll || 0) * D), 0); camera.lookAt(c.tx, c.ty, c.tz); camera.fov = c.fov; camera.updateProjectionMatrix(); }
  return { renderer, scene, camera, ctx, frame, post, aim };
}
