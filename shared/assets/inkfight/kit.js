// inkfight kit: flat-colour stickman fight animation on a 2D canvas (classic script, defines window.K).
// Rig + keyframes, camera shots + shake, impact FX, dusk city street, generic car, seatbelt diagram parts,
// post (bloom, grade, vignette, grain), safe-zone text helpers, poll. First used by videos/seatbelt-fight.
(function () {
const K = {};
K.W = 1080; K.H = 1920; K.FPS = 60;
// ---------- maths ----------
K.clamp = (v, a, b) => Math.max(a, Math.min(b, v));
K.lerp = (a, b, u) => a + (b - a) * u;
K.sm = u => { u = K.clamp(u, 0, 1); return u * u * (3 - 2 * u); };
K.ease = {
  l: u => u, h: u => 0,
  io: u => u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2,
  o: u => 1 - Math.pow(1 - u, 3),            // snap out (strikes)
  i: u => u * u * u,                          // ease in (anticipation into launch)
  back: u => { const c = 1.9; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); },
};
K.rng = seed => () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
K.noise = (t, s) => Math.sin(t * 37.1 + s * 11.3) * .5 + Math.sin(t * 61.7 + s * 3.7) * .3 + Math.sin(t * 97.3 + s) * .2;
const D = Math.PI / 180;
// ---------- keyframes ----------
// track: [[t, {fields}, ease], ...] ; fields missing in a key keep the previous key's value
K.track = keys => {
  const full = []; let prev = {};
  for (const [t, p, e] of keys) { prev = Object.assign({}, prev, p); full.push([t, prev, e || 'io']); }
  return t => {
    if (t <= full[0][0]) return Object.assign({}, full[0][1]);
    for (let i = 0; i < full.length - 1; i++) {
      const [t0, a] = full[i], [t1, b, e] = full[i + 1];
      if (t <= t1) {
        const u = K.ease[e]((t - t0) / Math.max(t1 - t0, 1e-6)), o = {};
        for (const k in b) o[k] = typeof b[k] === 'number' && typeof a[k] === 'number' ? K.lerp(a[k], b[k], u) : (u < 1 ? a[k] : b[k]);
        return o;
      }
    }
    return Object.assign({}, full[full.length - 1][1]);
  };
};
// ---------- rig ----------
// pose: x,y = hip (world, ground y=0, up negative); face +1 right / -1 left; lean (deg, + forward); head (deg);
// a1/a2 near arm (absolute shoulder angle from down, + forward; elbow bend), b1/b2 far arm; l1/l2 near leg (hip from down, knee bend, - = back), m1/m2 far leg;
// turn 0 profile .. 1 facing camera; sx/sy squash-stretch (sx < 0 = turned around, animate 1..-1..1 for a spin); rot = whole-body rotation (deg, + = backflip); s scale
K.BODY = { torso: 190, neck: 26, head: 54, up: 112, fore: 104, thigh: 138, shin: 132 };
K.joints = p => {
  const B = K.BODY, s = p.s || 1, f = p.face || 1, sx = p.sx || 1, sy = p.sy || 1;
  const rot = p.rot || 0, v = (a, len) => [Math.sin((a + rot) * D) * f * len * s * sx, Math.cos((a + rot) * D) * len * s * sy];
  const hip = [p.x, p.y], ln = p.lean || 0;
  const up = v(180 - ln, B.torso); const chest = [hip[0] + up[0], hip[1] + up[1]];
  const hv = v(180 - ln - (p.head || 0), B.neck + B.head); const head = [chest[0] + hv[0], chest[1] + hv[1]];
  const limb = (o, a, b, l1, l2, rel) => { const e = v(a + rel, l1); const j = [o[0] + e[0], o[1] + e[1]]; const g = v(a + b + rel, l2); return [j, [j[0] + g[0], j[1] + g[1]]]; };
  const [ea, ha] = limb(chest, p.a1 || 0, p.a2 || 0, B.up, B.fore, 0);   // arm angles are absolute (from straight down)
  const [eb, hb] = limb(chest, p.b1 || 0, p.b2 || 0, B.up, B.fore, 0);
  const [ka, fa] = limb(hip, p.l1 || 0, p.l2 || 0, B.thigh, B.shin, 0);
  const [kb, fb] = limb(hip, p.m1 || 0, p.m2 || 0, B.thigh, B.shin, 0);
  return { hip, chest, head, ea, ha, eb, hb, ka, fa, kb, fb, s, f: f * Math.sign(sx || 1) };
};
const seg = (c, a, b, w, col, rim) => {
  c.lineCap = 'round'; c.lineJoin = 'round'; c.strokeStyle = col; c.lineWidth = w;
  c.beginPath(); c.moveTo(a[0], a[1]); c.lineTo(b[0], b[1]); c.stroke();
  if (rim) { const ox = w * .3, oy = -w * .22; c.strokeStyle = rim; c.lineWidth = w * .26; c.beginPath(); c.moveTo(a[0] + ox, a[1] + oy); c.lineTo(b[0] + ox, b[1] + oy); c.stroke(); }
};
const poly = (c, a, b, wa, wb, col) => {   // tapered segment
  const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
  c.fillStyle = col; c.beginPath();
  c.moveTo(a[0] + nx * wa, a[1] + ny * wa); c.lineTo(b[0] + nx * wb, b[1] + ny * wb);
  c.lineTo(b[0] - nx * wb, b[1] - ny * wb); c.lineTo(a[0] - nx * wa, a[1] - ny * wa); c.closePath(); c.fill();
  c.beginPath(); c.arc(a[0], a[1], wa, 0, 7); c.arc(b[0], b[1], wb, 0, 7); c.fill();
};
K.PAL = {
  skin: '#9a6440', skinD: '#7a4c30', hair: '#1c1714', tee: '#f4f1ea', teeD: '#c9c6c0', shorts: '#16181d', shoe: '#f6f6f2', sole: '#14161a',
  glass: '#aab3bb', rim: 'rgba(255,190,110,.85)', rimC: 'rgba(120,230,255,.75)',
  red: '#ff4a3d', redD: '#b8302a', ink: '#0d1424',
};
const shoe = (c, k, f, s, P, far) => {
  const [x, y] = k; c.save(); c.translate(x, y); c.scale(f * s, s);
  c.fillStyle = far ? '#cfcfca' : P.shoe; c.beginPath(); c.roundRect(-14, -16, 50, 22, 10); c.fill();
  c.fillStyle = P.sole; c.fillRect(-14, 2, 50, 7); c.restore();
};
// main guy: dark messy hair, grey square glasses, brown skin, white tee, black shorts, white/black trainers
K.drawGuy = (c, p, o = {}) => {
  const J = K.joints(p), P = K.PAL, s = J.s, f = J.f, w = 24 * s, rim = o.rim === undefined ? P.rim : o.rim;
  // far limbs (darker)
  seg(c, J.hip, J.kb, w * 1.25, '#24272e'); seg(c, J.kb, J.fb, w, P.skinD); shoe(c, J.fb, f, s, P, 1);
  seg(c, J.chest, J.eb, w * 1.05, P.skinD); seg(c, J.eb, J.hb, w, P.skinD); c.fillStyle = P.skinD; c.beginPath(); c.arc(J.hb[0], J.hb[1], w * .78, 0, 7); c.fill();
  c.fillStyle = P.teeD; c.beginPath(); c.arc(J.chest[0], J.chest[1], w * .95, 0, 7); c.fill();
  // shorts + tee torso
  seg(c, J.hip, J.ka, w * 1.35, P.shorts);
  poly(c, J.hip, J.chest, w * 1.25, w * 1.45, P.tee);
  if (rim) { c.save(); c.globalAlpha = .9; seg(c, [J.hip[0], J.hip[1] - 4], [J.chest[0], J.chest[1] + 6], w * .9, 'rgba(0,0,0,0)', rim); c.restore(); }
  c.fillStyle = P.shorts; c.beginPath(); c.arc(J.hip[0], J.hip[1], w * 1.3, 0, 7); c.fill();
  // near leg
  const kneeMid = [K.lerp(J.hip[0], J.ka[0], .9), K.lerp(J.hip[1], J.ka[1], .9)];
  seg(c, J.ka, J.fa, w, P.skin, rim); seg(c, J.hip, kneeMid, w * 1.35, P.shorts); shoe(c, J.fa, f, s, P);
  // head
  K.drawGuyHead(c, J.head, Object.assign({}, p, { face: J.f }), s, o);
  // near arm: sleeve + skin
  const sl = [K.lerp(J.chest[0], J.ea[0], .42), K.lerp(J.chest[1], J.ea[1], .42)];
  seg(c, J.ea, J.ha, w * .95, P.skin, rim); seg(c, sl, J.ea, w, P.skin, rim); seg(c, J.chest, sl, w * 1.35, P.tee);
  c.fillStyle = P.skin; c.beginPath(); c.arc(J.ha[0], J.ha[1], w * .82, 0, 7); c.fill();
  if (o.thumb) { c.save(); c.translate(J.ha[0], J.ha[1]); c.fillStyle = P.skin; c.beginPath(); c.roundRect(-6 * s, -34 * s, 13 * s, 30 * s, 6 * s); c.fill(); c.restore(); }
  return J;
};
K.drawGuyHead = (c, h, p, s, o = {}) => {
  const P = K.PAL, r = K.BODY.head * s, f = p.face || 1, tu = K.clamp(p.turn || 0, 0, 1), ang = (((p.lean || 0) + (p.head || 0)) * (1 - tu * .7) - (p.rot || 0)) * D * f;
  c.save(); c.translate(h[0], h[1]); c.rotate(ang);
  c.fillStyle = P.skin; c.beginPath(); c.arc(0, 0, r, 0, 7); c.fill();
  // ear (profile only)
  if (tu < .8) { c.fillStyle = P.skinD; c.beginPath(); c.ellipse(-f * r * .18 * (1 - tu), r * .05, r * .16, r * .2, 0, 0, 7); c.fill(); }
  // hair: cap + messy tufts, shifted to the back in profile
  const hx = -f * r * .18 * (1 - tu);
  c.fillStyle = P.hair; c.beginPath();
  c.ellipse(hx, -r * .42, r * 1.06, r * .7, 0, Math.PI, 0); c.fill();
  c.beginPath(); c.ellipse(hx - f * r * .45 * (1 - tu), -r * .12, r * .55, r * .5, 0, 0, 7); c.fill();
  for (let i = 0; i < 5; i++) { const a = -2.6 + i * .5; c.beginPath(); c.ellipse(hx + Math.cos(a) * r * .86, -r * .4 + Math.sin(a) * r * .62, r * .3, r * .2, a + 1.3, 0, 7); c.fill(); }
  c.beginPath(); c.moveTo(hx - r * .2, -r * 1.0); c.quadraticCurveTo(hx + r * .2, -r * 1.42, hx + r * .5, -r * 1.12); c.quadraticCurveTo(hx + r * .2, -r * 1.12, hx - r * .2, -r * 1.0); c.fill();
  // fringe edge
  c.beginPath(); c.moveTo(-r * .95, -r * .25); c.quadraticCurveTo(0, -r * .62, r * .95, -r * .3); c.lineTo(r * .9, -r * .7); c.lineTo(-r * .9, -r * .7); c.fill();
  // face features
  const fx = f * r * .42 * (1 - tu), sep = r * .42 * tu, eyeY = -r * .02, lw = Math.max(3, r * .085);
  const blink = o.blink ? .15 : 1, look = (o.look || 0) * r * .06;
  const eyes = tu < .25 ? [fx + f * r * .1] : [fx - sep, fx + sep];
  c.fillStyle = '#16120f';
  for (const ex of eyes) { c.beginPath(); c.ellipse(ex + look, eyeY, r * .085, r * .12 * blink, 0, 0, 7); c.fill(); }
  // brows
  c.strokeStyle = P.hair; c.lineCap = 'round'; c.lineWidth = r * .1; const br = o.brow || 0;
  for (const ex of eyes) { c.beginPath(); c.moveTo(ex - r * .17, eyeY - r * .3 - br * r * .1); c.lineTo(ex + r * .17, eyeY - r * .33 - br * r * .14); c.stroke(); }
  // glasses: grey square frames
  c.strokeStyle = P.glass; c.lineWidth = lw; c.fillStyle = 'rgba(190,225,255,.16)';
  for (const ex of eyes) { c.beginPath(); c.roundRect(ex - r * .26, eyeY - r * .2, r * .52, r * .38, r * .07); c.fill(); c.stroke(); }
  if (eyes.length === 2) { c.beginPath(); c.moveTo(eyes[0] + r * .26, eyeY - r * .05); c.lineTo(eyes[1] - r * .26, eyeY - r * .05); c.stroke(); }
  else { c.beginPath(); c.moveTo(eyes[0] - f * r * .26, eyeY - r * .04); c.lineTo(-f * r * .25, eyeY - r * .02); c.stroke(); }
  // cheeks + mouth (open from voice loudness)
  c.fillStyle = 'rgba(230,120,110,.28)'; for (const ex of eyes) { c.beginPath(); c.ellipse(ex, r * .3, r * .12, r * .07, 0, 0, 7); c.fill(); }
  const m = K.clamp(o.mouth || 0, 0, 1), mx = tu < .25 ? fx + f * r * .05 : fx * .3, my = r * .5;
  c.fillStyle = '#3a1712';
  if (m < .08) { c.strokeStyle = '#3a1712'; c.lineWidth = r * .07; c.beginPath(); c.arc(mx, my - r * .1, r * .17 * (o.smile === 0 ? .5 : 1), .3, Math.PI - .3); c.stroke(); }
  else { c.beginPath(); c.ellipse(mx, my, r * (.13 + .06 * m) * (tu < .25 ? .7 : 1), r * (.05 + .17 * m), 0, 0, 7); c.fill();
    c.fillStyle = '#d9645a'; c.beginPath(); c.ellipse(mx, my + r * .1 * m, r * .08, r * .05 * m, 0, 0, 7); c.fill(); }
  // rim light on head
  if (o.rim !== null) { c.strokeStyle = o.rim || P.rim; c.lineWidth = r * .12; c.beginPath(); c.arc(0, 0, r * .93, -1.2, .1); c.stroke(); }
  c.restore();
};
// opponent: vermilion stickman silhouette, no face, white headband tails
K.drawRival = (c, p, o = {}) => {
  const J = K.joints(p), P = Object.assign({}, K.PAL, o.pal || {}), s = J.s, w = 24 * s, rim = o.rim || P.rimC;
  seg(c, J.hip, J.kb, w, P.redD); seg(c, J.kb, J.fb, w, P.redD);
  seg(c, J.chest, J.eb, w, P.redD); seg(c, J.eb, J.hb, w, P.redD);
  c.fillStyle = P.redD; c.beginPath(); c.arc(J.hb[0], J.hb[1], w * .85, 0, 7); c.arc(J.fb[0], J.fb[1], w * .7, 0, 7); c.fill();
  poly(c, J.hip, J.chest, w * .62, w * .62, P.red);
  seg(c, [J.hip[0], J.hip[1] - 4], [J.chest[0], J.chest[1] + 4], w * .9, 'rgba(0,0,0,0)', rim);
  seg(c, J.hip, J.ka, w, P.red, rim); seg(c, J.ka, J.fa, w, P.red, rim);
  c.fillStyle = P.red; c.beginPath(); c.arc(J.fa[0], J.fa[1], w * .7, 0, 7); c.fill();
  const r = K.BODY.head * s; c.save(); c.translate(J.head[0], J.head[1]);
  c.fillStyle = P.red; c.beginPath(); c.arc(0, 0, r, 0, 7); c.fill();
  if (o.cap) { c.fillStyle = o.cap; c.beginPath(); c.arc(0, -r * .1, r * 1.02, Math.PI * 1.05, Math.PI * 1.95); c.fill(); c.fillRect(J.f > 0 ? 0 : -r * 1.5, -r * .5, r * 1.5, r * .22); }
  if (o.band !== false) c.fillStyle = '#fff4ea', c.fillRect(-r, -r * .38, 2 * r, r * .2);
  const tt = o.t || 0, bx = -J.f * r;
  c.strokeStyle = '#fff4ea'; c.lineWidth = r * .14; c.lineCap = 'round';
  for (let i = 0; i < (o.band === false ? 0 : 2); i++) { c.beginPath(); c.moveTo(bx, -r * .28); c.quadraticCurveTo(bx - J.f * r * .6, -r * (.25 - i * .3) + Math.sin(tt * 18 + i) * r * .15, bx - J.f * r * (1.1 + i * .2), -r * (.1 - i * .4) + Math.sin(tt * 21 + i) * r * .25); c.stroke(); }
  c.strokeStyle = rim; c.lineWidth = r * .12; c.beginPath(); c.arc(0, 0, r * .93, -1.2, .1); c.stroke();
  c.restore();
  seg(c, J.chest, J.ea, w, P.red, rim); seg(c, J.ea, J.ha, w, P.red, rim);
  c.fillStyle = P.red; c.beginPath(); c.arc(J.ha[0], J.ha[1], w * .9, 0, 7); c.fill();
  if (o.thumb) { c.fillRect(J.ha[0] - 6 * s, J.ha[1] - 34 * s, 13 * s, 30 * s); }
  return J;
};
// smear ribbon: pts newest first [[x,y],...]
K.smear = (c, pts, w, col) => {
  if (pts.length < 2) return; let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  if (L < 25) return;
  c.save(); c.lineCap = 'round';
  for (let i = 1; i < pts.length; i++) { const u = i / pts.length; c.globalAlpha = .55 * (1 - u); c.strokeStyle = col; c.lineWidth = w * (1 - u * .8);
    c.beginPath(); c.moveTo(pts[i - 1][0], pts[i - 1][1]); c.lineTo(pts[i][0], pts[i][1]); c.stroke(); }
  c.globalAlpha = .9; c.strokeStyle = 'rgba(255,255,255,.85)'; c.lineWidth = 4;
  c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) c.lineTo(pts[i][0] + (i % 2 ? 3 : -3), pts[i][1]); c.stroke();
  c.restore();
};
K.crack = (c, x, age, seed, size = 260) => { if (age < 0 || age > 1.6) return; const r = K.rng(seed); c.save(); c.globalAlpha = Math.min(1, (1.6 - age) / .4);
  c.strokeStyle = '#05060c'; c.lineWidth = 7; c.lineCap = 'round';
  for (let i = 0; i < 7; i++) { let px = x, py = 4; const dir = i < 3.5 ? -1 : 1; c.beginPath(); c.moveTo(px, py);
    for (let k = 0; k < 4; k++) { px += dir * (20 + r() * size * .3); py += (r() - .3) * 26; c.lineTo(px, py); } c.stroke(); }
  c.strokeStyle = 'rgba(255,190,110,.6)'; c.lineWidth = 3; c.beginPath(); c.ellipse(x, 6, size * K.ease.o(Math.min(age / .3, 1)), 24, 0, 0, 7); c.stroke(); c.restore(); };
K.shockwave = (c, x, y, age, size) => { if (age < 0 || age > .6) return; const u = age / .6; c.save();
  c.globalAlpha = 1 - u; c.strokeStyle = '#ffffff'; c.lineWidth = 26 * (1 - u); c.beginPath(); c.ellipse(x, y, size * K.ease.o(u), size * .55 * K.ease.o(u), 0, 0, 7); c.stroke();
  c.strokeStyle = '#ffb347'; c.lineWidth = 10 * (1 - u); c.beginPath(); c.ellipse(x, y, size * .7 * K.ease.o(u), size * .38 * K.ease.o(u), 0, 0, 7); c.stroke(); c.restore(); };
K.shadow = (c, x, w, a = .45) => { c.fillStyle = `rgba(5,8,18,${a})`; c.beginPath(); c.ellipse(x, 4, w, w * .12, 0, 0, 7); c.fill(); };
// ---------- FX ----------
K.burst = (c, x, y, age, size, seed, col = '#fff6dc') => {
  if (age < 0 || age > .32) return; const r = K.rng(seed), u = age / .32, R = size * (.6 + .6 * K.ease.o(u));
  c.save(); c.translate(x, y); c.globalAlpha = 1 - u * u;
  c.fillStyle = col; c.beginPath(); const n = 14;
  for (let i = 0; i < n * 2; i++) { const a = i / (n * 2) * Math.PI * 2 + r() * .15, rr = i % 2 ? R * (.25 + r() * .15) : R * (.7 + r() * .5); c.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); }
  c.closePath(); c.fill();
  c.fillStyle = '#ffb347'; c.beginPath(); c.arc(0, 0, R * .28 * (1 - u), 0, 7); c.fill();
  c.strokeStyle = '#fff'; c.lineWidth = 10 * (1 - u); c.beginPath(); c.arc(0, 0, size * (.4 + 1.6 * K.ease.o(u)), 0, 7); c.stroke();
  c.strokeStyle = '#5fe3ff'; c.lineWidth = 5 * (1 - u); c.beginPath(); c.arc(0, 0, size * (.3 + 2.2 * K.ease.o(u)), 0, 7); c.stroke();
  c.restore();
};
K.sparks = (c, x, y, age, n, seed, spd = 900, g = 1600) => {
  if (age < 0 || age > .9) return; const r = K.rng(seed); c.save(); c.lineCap = 'round';
  for (let i = 0; i < n; i++) { const a = r() * Math.PI * 2, v = spd * (.4 + r() * .8), life = .35 + r() * .5; if (age > life) continue;
    const px = x + Math.cos(a) * v * age, py = y + Math.sin(a) * v * age + g * age * age * .5, vx = Math.cos(a) * v, vy = Math.sin(a) * v + g * age;
    c.globalAlpha = 1 - age / life; c.strokeStyle = i % 3 ? '#ffd27a' : '#ffffff'; c.lineWidth = 5;
    c.beginPath(); c.moveTo(px, py); c.lineTo(px - vx * .025, py - vy * .025); c.stroke(); }
  c.restore();
};
K.dust = (c, x, y, age, n, seed, size = 60, dir = 0) => {
  if (age < 0 || age > 1.2) return; const r = K.rng(seed); c.save();
  for (let i = 0; i < n; i++) { const a = Math.PI + r() * Math.PI, v = 150 + r() * 260, u = age / 1.2;
    const px = x + Math.cos(a) * v * K.ease.o(u) + dir * v * u, py = y + Math.sin(a) * v * .35 * K.ease.o(u);
    c.globalAlpha = .45 * (1 - u); c.fillStyle = i % 2 ? '#8d93a8' : '#b5b9c8';
    c.beginPath(); c.arc(px, py, size * (.4 + r() * .5) * (.5 + u), 0, 7); c.fill(); }
  c.restore();
};
K.speedLines = (c, cx, cy, age, seed, dirx = 1, len = 600) => {
  const r = K.rng(seed); c.save(); c.strokeStyle = 'rgba(255,255,255,.55)'; c.lineCap = 'round';
  for (let i = 0; i < 16; i++) { const y = cy + (r() - .5) * 900, x = cx + (r() - .5) * 900 - dirx * age * 2400 * (.6 + r());
    c.lineWidth = 3 + r() * 5; c.beginPath(); c.moveTo(x, y); c.lineTo(x - dirx * len * (.4 + r()), y); c.stroke(); }
  c.restore();
};
// ---------- camera ----------
// shots: [{t0, t1, a:{x,y,z,r}, b:{x,y,z,r}, e}] ; hard cut at each t0
K.camera = (shots, impacts) => t => {
  let s = shots[0]; for (const q of shots) if (t >= q.t0) s = q;
  const u = K.ease[s.e || 'io'](K.clamp((t - s.t0) / (s.t1 - s.t0), 0, 1)), cam = {};
  for (const k of ['x', 'y', 'z', 'r']) cam[k] = K.lerp(s.a[k] || 0, (s.b || s.a)[k] === undefined ? (s.a[k] || 0) : (s.b || s.a)[k], u);
  let sh = 0; for (const im of impacts) { const a = t - im.t; if (a >= 0 && a < .5) sh += im.shake * Math.exp(-a * 9); }
  cam.x += K.noise(t, 1) * sh / cam.z; cam.y += K.noise(t, 2) * sh / cam.z; cam.r += K.noise(t, 3) * sh * .0004; cam.shot = s;
  return cam;
};
K.apply = (c, cam) => { c.translate(K.W / 2, K.H / 2); c.rotate(cam.r || 0); c.scale(cam.z, cam.z); c.translate(-cam.x, -cam.y); };
// ---------- dusk city street ----------
K.buildStreet = (x0, x1) => {
  const r = K.rng(42), Wd = x1 - x0;
  const mk = (h) => { const cv = document.createElement('canvas'); cv.width = Math.ceil(Wd / 2); cv.height = h; return cv; };
  // far: sky + skyline (drawn at half res, blurred); y origin = world -1700
  const far = mk(1100), f = far.getContext('2d');
  const g = f.createLinearGradient(0, 0, 0, 1100);
  g.addColorStop(0, '#1a1d48'); g.addColorStop(.42, '#5a3a78'); g.addColorStop(.7, '#d4687a'); g.addColorStop(.88, '#ffb36b'); g.addColorStop(1, '#ffcf8a');
  f.fillStyle = g; f.fillRect(0, 0, far.width, 1100);
  f.fillStyle = 'rgba(255,240,220,.7)'; for (let i = 0; i < 60; i++) { f.beginPath(); f.arc(r() * far.width, r() * 300, r() * 1.6 + .3, 0, 7); f.fill(); }
  const sky = (col, hmin, hmax, win, base) => { let x = -20; while (x < far.width) { const w = 40 + r() * 90, h = hmin + r() * (hmax - hmin);
      f.fillStyle = col; f.fillRect(x, base - h, w, h + 400); if (r() < .3) f.fillRect(x + w * .4, base - h - 30 - r() * 40, 4, 40 + r() * 30);
      if (win) { for (let yy = base - h + 12; yy < base - 8; yy += 16) for (let xx = x + 8; xx < x + w - 8; xx += 13) if (r() < .32) { f.fillStyle = r() < .7 ? 'rgba(255,200,120,.85)' : 'rgba(140,230,255,.7)'; f.fillRect(xx, yy, 6, 8); } }
      x += w + r() * 10; } };
  sky('#4b3a6e', 120, 380, false, 900); sky('#2b2550', 160, 470, true, 960); sky('#1b1838', 90, 300, true, 1000);
  f.filter = 'blur(3px)'; f.drawImage(far, 0, 0); f.filter = 'none';
  // mid: streetlights + blank neon signs + bokeh (world y -1700..0)
  const mid = mk(1000), m = mid.getContext('2d');
  for (let x = 60; x < mid.width; x += 380 + r() * 140) {
    m.fillStyle = '#121227'; m.fillRect(x, 260, 9, 740); m.fillRect(x - 40, 258, 50, 8);
    const gg = m.createRadialGradient(x - 40, 266, 2, x - 40, 266, 120); gg.addColorStop(0, 'rgba(255,214,150,.95)'); gg.addColorStop(.25, 'rgba(255,170,90,.35)'); gg.addColorStop(1, 'rgba(255,170,90,0)');
    m.fillStyle = gg; m.fillRect(x - 160, 146, 240, 240);
  }
  const neon = ['#ff5fa2', '#5fe3ff', '#ffd35f', '#9c7bff'];
  for (let i = 0; i < Wd / 300; i++) { const x = r() * mid.width, y = 380 + r() * 380, w = 50 + r() * 90, h = 24 + r() * 50, col = neon[i % 4];
    m.save(); m.shadowColor = col; m.shadowBlur = 30; m.strokeStyle = col; m.lineWidth = 6; m.beginPath(); m.roundRect(x, y, w, h, 10); m.stroke();
    m.fillStyle = col; m.globalAlpha = .55; m.fillRect(x + 12, y + h * .4, w - 24, 5); m.restore(); }
  for (let i = 0; i < Wd / 40; i++) { const x = r() * mid.width, y = 300 + r() * 650, rr = 8 + r() * 22; m.fillStyle = `rgba(${r() < .5 ? '255,190,120' : '120,220,255'},${.12 + r() * .25})`; m.beginPath(); m.arc(x, y, rr, 0, 7); m.fill(); }
  const mb = mk(1000), mbc = mb.getContext('2d'); mbc.filter = 'blur(5px)'; mbc.drawImage(mid, 0, 0);
  return { x0, far, mid: mb, seedWet: 7 };
};
// draw street for camera cam (world space already applied to ctx)
K.drawStreet = (c, S, cam, t) => {
  const vw = K.W / cam.z, vh = K.H / cam.z, L = cam.x - vw / 2 - 200, R = cam.x + vw / 2 + 200;
  // parallax layers: drawn in world space with offset so they move slower than the ground
  const lay = (img, k, y0, h) => { const ox = cam.x * k; c.drawImage(img, (L - ox - S.x0) / 2, 0, (R - L) / 2, img.height, L, y0 + cam.y * k * .5, R - L, h); };
  c.fillStyle = '#1a1d48'; c.fillRect(L, cam.y - vh, R - L, vh * 2);
  lay(S.far, .8, -2400, 2200); lay(S.mid, .45, -2000, 2000);
  // sidewalk + wet road
  const g = c.createLinearGradient(0, -40, 0, 900); g.addColorStop(0, '#2a2547'); g.addColorStop(.25, '#1b1a33'); g.addColorStop(1, '#0c0d1b');
  c.fillStyle = g; c.fillRect(L, -40, R - L, 1400);
  c.fillStyle = '#3a3358'; c.fillRect(L, -46, R - L, 10);
  // reflections of the lights (vertical soft streaks)
  const step = 380; for (let x = Math.floor(L / step) * step; x < R; x += step) { const xx = x + 30, rg = c.createLinearGradient(0, 0, 0, 700);
    rg.addColorStop(0, 'rgba(255,190,120,.16)'); rg.addColorStop(1, 'rgba(255,190,120,0)'); c.fillStyle = rg; c.save(); c.filter = 'blur(10px)'; c.fillRect(xx - 14 + Math.sin(t * 2 + x) * 3, 10, 28, 600); c.restore();
    const rg2 = c.createLinearGradient(0, 0, 0, 500); rg2.addColorStop(0, 'rgba(110,220,255,.1)'); rg2.addColorStop(1, 'rgba(110,220,255,0)'); c.fillStyle = rg2; c.fillRect(xx + 170, 10, 22, 420); }
  c.fillStyle = 'rgba(240,235,220,.55)'; for (let x = Math.floor(L / 260) * 260; x < R; x += 260) c.fillRect(x, 300, 140, 12);
};
// ---------- generic car (no badge, blank plate) ----------
// side view, centre bottom at (x, 0), facing f (-1 = left). crush 0..1 shortens/crumples the front. occupant(c) draws inside.
K.CAR = { len: 1480, h: 520, wheel: 112 };
K.drawCar = (c, x, f, o = {}) => {
  const C = K.CAR, cr = o.crush || 0, L = C.len / 2, y0 = -(o.lift || 0);
  c.save(); c.translate(x, y0); c.rotate((o.pitch || 0) * D); c.scale(f, 1);   // local +x = front
  const fr = L - cr * 170;
  const body = () => { c.beginPath(); c.moveTo(-L, -140); c.lineTo(-L + 10, -300); c.quadraticCurveTo(-L + 40, -330, -L + 150, -340);
    c.lineTo(-L + 360, -500); c.quadraticCurveTo(-L + 420, -C.h, -L + 520, -C.h); c.lineTo(160, -C.h + 6); c.quadraticCurveTo(250, -C.h + 4, 330, -390);
    c.lineTo(fr - 120 - cr * 30, -340 + cr * 40); c.quadraticCurveTo(fr - 20, -320 + cr * 30, fr, -250 + cr * 50); c.lineTo(fr - cr * 20, -120);
    c.quadraticCurveTo(fr, -70, fr - 30, -60); c.lineTo(-L + 20, -60); c.quadraticCurveTo(-L, -80, -L, -140); c.closePath(); };
  // interior (behind glass): seat, wheel, occupant
  c.save(); body(); c.clip();
  c.fillStyle = '#10142a'; c.fillRect(-L, -C.h, 2 * L, C.h);
  c.restore();
  if (o.occupant) { c.save(); c.beginPath(); c.moveTo(-L + 380, -480); c.lineTo(-L + 380, -150); c.lineTo(330, -150); c.lineTo(330, -400); c.lineTo(160, -495); c.closePath(); c.clip(); o.occupant(c); c.restore(); }
  // body paint with cutout windows
  const g = c.createLinearGradient(0, -C.h, 0, -60); g.addColorStop(0, o.col2 || '#ffcf6a'); g.addColorStop(.5, o.col || '#f2a33a'); g.addColorStop(1, o.col3 || '#1d5f73');
  c.save(); body(); c.fillStyle = g;
  c.beginPath(); body(); c.moveTo(-L + 400, -470); c.lineTo(-L + 400, -395); c.lineTo(-30, -395); c.lineTo(-30, -490); c.lineTo(-L + 430, -490); c.closePath();
  c.moveTo(-10, -490); c.lineTo(-10, -395); c.lineTo(305, -395); c.lineTo(150, -488); c.closePath();
  if (o.doorOff) { c.moveTo(-L + 400, -395); c.lineTo(-L + 400, -170); c.lineTo(300, -170); c.lineTo(305, -395); c.closePath(); }
  c.fill('evenodd'); c.restore();
  // window glass tint
  c.fillStyle = `rgba(120,200,255,${o.glass === undefined ? .14 : o.glass})`;
  c.beginPath(); c.moveTo(-L + 400, -470); c.lineTo(-L + 400, -395); c.lineTo(-30, -395); c.lineTo(-30, -490); c.lineTo(-L + 430, -490); c.closePath(); c.fill();
  c.beginPath(); c.moveTo(-10, -490); c.lineTo(-10, -395); c.lineTo(305, -395); c.lineTo(150, -488); c.closePath(); c.fill();
  // shine line, door seams, handle, lights
  c.strokeStyle = 'rgba(255,245,220,.7)'; c.lineWidth = 6; c.beginPath(); c.moveTo(-L + 160, -330); c.lineTo(fr - 140, -335 + cr * 30); c.stroke();
  c.strokeStyle = 'rgba(10,40,55,.55)'; c.lineWidth = 4; if (!o.doorOff) { c.beginPath(); c.moveTo(-20, -395); c.lineTo(-20, -90); c.moveTo(300, -390); c.lineTo(310, -100); c.stroke();
    c.fillStyle = 'rgba(10,40,55,.6)'; c.fillRect(-120, -300, 60, 12); }
  c.fillStyle = '#fff4c8'; c.beginPath(); c.ellipse(fr - 40, -280 + cr * 40, 34, 18, -.3, 0, 7); c.fill();
  c.fillStyle = '#ff3d4a'; c.fillRect(-L + 4, -300, 20, 70);
  c.fillStyle = '#e8e4da'; c.fillRect(fr - 60, -165, 56, 30);   // blank plate
  if (cr > 0) { c.strokeStyle = '#0f3a48'; c.lineWidth = 6; c.beginPath(); for (let i = 0; i < 6; i++) { const xx = fr - 30 - i * 26; c.lineTo(xx, -300 + (i % 2) * 60 + cr * 20); } c.stroke(); }
  // wheels
  const wr = C.wheel, rot = o.spin || 0;
  for (const wx of [-L + 300, L - 310 - cr * 60]) { c.save(); c.translate(wx, -wr * .98); c.fillStyle = '#121318'; c.beginPath(); c.arc(0, 0, wr, 0, 7); c.fill();
    c.fillStyle = '#c9ccd4'; c.beginPath(); c.arc(0, 0, wr * .55, 0, 7); c.fill(); c.rotate(rot); c.fillStyle = '#6b6f7a';
    for (let i = 0; i < 5; i++) { c.rotate(Math.PI * 2 / 5); c.fillRect(-8, -wr * .5, 16, wr * .42); } c.fillStyle = '#2a2c33'; c.beginPath(); c.arc(0, 0, 12, 0, 7); c.fill(); c.restore(); }
  c.restore();
};
// ---------- seatbelt diagram parts (screen space, flat) ----------
K.DG = { belt: '#ffb347', beltD: '#c97a1c', seat: '#3c4a78', seatD: '#2c3760', body: '#efe6d6', metal: '#c9ced8', metalD: '#7f8696', charge: '#ff4a3d', cyan: '#5fe3ff' };
K.seatShape = (c, x, y, s) => { const G = K.DG; c.save(); c.translate(x, y); c.scale(s, s);
  c.fillStyle = G.seatD; c.beginPath(); c.roundRect(-30, -40, 220, 70, 30); c.fill();
  c.fillStyle = G.seat; c.save(); c.translate(150, -40); c.rotate(.18); c.beginPath(); c.roundRect(-20, -330, 75, 340, 34); c.fill(); c.beginPath(); c.roundRect(-5, -420, 60, 85, 22); c.fill(); c.restore(); c.restore(); };
K.dummy = (c, x, y, s, lean) => { const G = K.DG; c.save(); c.translate(x, y); c.scale(s, s); c.rotate(-lean * D);
  c.strokeStyle = G.body; c.lineCap = 'round'; c.lineWidth = 34;
  c.beginPath(); c.moveTo(130, -20); c.lineTo(-40, -20); c.lineTo(-60, 120); c.stroke();
  c.beginPath(); c.moveTo(130, -20); c.lineTo(160, -260); c.stroke();
  c.beginPath(); c.moveTo(155, -230); c.lineTo(60, -150); c.lineTo(-20, -190); c.stroke();
  c.fillStyle = G.body; c.beginPath(); c.arc(170, -330, 50, 0, 7); c.fill(); c.restore();
  const a = -lean * D, rx = (px, py) => [x + s * (px * Math.cos(a) - py * Math.sin(a)), y + s * (px * Math.sin(a) + py * Math.cos(a))];
  return { shoulder: rx(185, -235), hip: rx(110, -10), chest: rx(150, -150) };
};
K.spool = (c, x, y, r, ang, wound) => { const G = K.DG; c.save(); c.translate(x, y);
  c.fillStyle = G.metalD; c.beginPath(); c.roundRect(-r * 1.3, -r * 1.3, r * 2.6, r * 2.6, r * .3); c.fill();
  c.fillStyle = G.beltD; c.beginPath(); c.arc(0, 0, r * (.45 + .5 * wound), 0, 7); c.fill();
  c.strokeStyle = 'rgba(0,0,0,.25)'; c.lineWidth = 3; for (let k = .5; k < .45 + .5 * wound; k += .09) { c.beginPath(); c.arc(0, 0, r * k, 0, 7); c.stroke(); }
  c.rotate(ang); c.fillStyle = G.metal; c.beginPath(); c.arc(0, 0, r * .42, 0, 7); c.fill();
  c.fillStyle = G.metalD; for (let i = 0; i < 6; i++) { c.rotate(Math.PI / 3); c.beginPath(); c.moveTo(r * .2, -6); c.lineTo(r * .4, -10); c.lineTo(r * .4, 10); c.lineTo(r * .2, 6); c.fill(); }
  c.fillStyle = '#20263d'; c.beginPath(); c.arc(0, 0, r * .12, 0, 7); c.fill(); c.restore(); };
K.cartridge = (c, x, y, s, fire) => { const G = K.DG; c.save(); c.translate(x, y); c.scale(s, s);
  c.fillStyle = G.metal; c.beginPath(); c.roundRect(-90, -26, 150, 52, 14); c.fill(); c.fillStyle = G.charge; c.beginPath(); c.roundRect(-110, -22, 40, 44, 10); c.fill();
  if (fire > 0 && fire < 1) { const u = fire; c.globalAlpha = 1 - u; c.fillStyle = '#fff1c4'; for (let i = 0; i < 7; i++) { const a = i / 7 * 6.28; c.beginPath(); c.arc(-90 + Math.cos(a) * 60 * u, Math.sin(a) * 60 * u, 26 * (1 - u * .5), 0, 7); c.fill(); }
    c.fillStyle = '#ffb347'; c.beginPath(); c.arc(-90, 0, 46 * (1 - u), 0, 7); c.fill(); }
  c.restore(); };
K.motor = (c, x, y, s, ang) => { const G = K.DG; c.save(); c.translate(x, y); c.scale(s, s);
  c.fillStyle = '#3d4566'; c.beginPath(); c.roundRect(-100, -38, 130, 76, 16); c.fill(); c.fillStyle = G.cyan; c.fillRect(-84, -26, 8, 52); c.fillRect(-66, -26, 8, 52); c.fillRect(-48, -26, 8, 52);
  c.translate(48, 0); c.rotate(ang); c.fillStyle = G.metal; c.beginPath(); for (let i = 0; i < 16; i++) { const a = i / 16 * 6.28, rr = i % 2 ? 26 : 34; c.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); } c.fill(); c.restore(); };
K.arrow = (c, x0, y0, x1, y1, col, w = 10) => { const a = Math.atan2(y1 - y0, x1 - x0); c.save(); c.strokeStyle = col; c.fillStyle = col; c.lineWidth = w; c.lineCap = 'round';
  c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1 - Math.cos(a) * w * 1.5, y1 - Math.sin(a) * w * 1.5); c.stroke();
  c.beginPath(); c.moveTo(x1, y1); c.lineTo(x1 - Math.cos(a - .5) * w * 3, y1 - Math.sin(a - .5) * w * 3); c.lineTo(x1 - Math.cos(a + .5) * w * 3, y1 - Math.sin(a + .5) * w * 3); c.fill(); c.restore(); };
K.airbag = (c, x, y, u, f) => { if (u <= 0) return; const r = 150 * K.ease.back(K.clamp(u, 0, 1)); c.save(); c.translate(x, y);
  c.fillStyle = '#f3efe6'; c.beginPath(); c.ellipse(-f * r * .55, -r * .1, r * .62, r, 0, 0, 7); c.fill();
  c.strokeStyle = 'rgba(150,150,160,.5)'; c.lineWidth = 5; c.beginPath(); c.ellipse(-f * r * .55, -r * .1, r * .4, r * .7, 0, -1, 1); c.stroke(); c.restore(); };
// ---------- post ----------
K.makePost = () => {
  const small = document.createElement('canvas'); small.width = 270; small.height = 480; const sc = small.getContext('2d');
  const grains = []; const r = K.rng(99);
  for (let k = 0; k < 6; k++) { const g = document.createElement('canvas'); g.width = 540; g.height = 960; const gc = g.getContext('2d'), im = gc.createImageData(540, 960);
    for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() - .5) * 120; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } gc.putImageData(im, 0, 0); grains.push(g); }
  return (c, frame, o = {}) => {
    c.save(); c.setTransform(1, 0, 0, 1, 0, 0);
    sc.filter = 'blur(5px)'; sc.clearRect(0, 0, 270, 480); sc.drawImage(c.canvas, 0, 0, 270, 480); sc.filter = 'none';
    c.globalCompositeOperation = 'screen'; c.globalAlpha = o.bloom === undefined ? .32 : o.bloom; c.drawImage(small, 0, 0, K.W, K.H);
    c.globalAlpha = 1; c.globalCompositeOperation = 'soft-light';
    const g = c.createLinearGradient(0, 0, 0, K.H); g.addColorStop(0, 'rgba(80,120,255,.35)'); g.addColorStop(1, 'rgba(255,150,70,.3)'); c.fillStyle = g; c.fillRect(0, 0, K.W, K.H);
    c.globalCompositeOperation = 'source-over';
    const v = c.createRadialGradient(K.W / 2, K.H * .48, K.H * .28, K.W / 2, K.H * .5, K.H * .72); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(4,6,16,.62)');
    c.fillStyle = v; c.fillRect(0, 0, K.W, K.H);
    c.globalCompositeOperation = 'overlay'; c.globalAlpha = .07; c.drawImage(grains[frame % grains.length], 0, 0, K.W, K.H);
    c.restore();
  };
};
// ---------- text (logs every box for the safe-zone check) ----------
K.SAFE = { y0: .12 * 1920, y1: .62 * 1920, x1: .85 * 1080 };
K.boxes = [];
K.text = (c, str, x, y, o = {}) => {   // x,y = left/top (o.center: x is the centre)
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0);
  c.font = `${o.weight || 900} ${o.size || 64}px ${o.font || '"Inter Display", Inter, sans-serif'}`; c.textBaseline = 'top';
  const w = c.measureText(str).width, h = (o.size || 64) * 1.12, x0 = o.center ? x - w / 2 : x, pad = o.pad || 0;
  if (o.alpha !== undefined) c.globalAlpha = o.alpha;
  if (o.plate) { c.fillStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.roundRect(x0 - pad + 4, y - pad * .6 + 8, w + 2 * pad, h + pad * 1.2, (h + pad) * .4); c.fill();
    c.fillStyle = o.plate; c.beginPath(); c.roundRect(x0 - pad, y - pad * .6, w + 2 * pad, h + pad * 1.2, (h + pad) * .4); c.fill(); }
  if (o.stroke) { c.lineJoin = 'round'; c.strokeStyle = o.stroke; c.lineWidth = o.sw || 12; c.strokeText(str, x0, y + (o.size || 64) * .06); }
  if (o.parts) { let xx = x0; for (const [s, col] of o.parts) { c.fillStyle = col; c.fillText(s, xx, y + (o.size || 64) * .06); xx += c.measureText(s).width; } }
  else { c.fillStyle = o.color || '#fff'; c.fillText(str, x0, y + (o.size || 64) * .06); }
  c.restore();
  const b = { s: str, x: x0 - pad, y: y - pad * .6, w: w + 2 * pad, h: h + pad * 1.2 }; if (!o.noLog) K.boxes.push(b); return b;
};
// poll sticker: two options, white card; returns its boxes
K.poll = (c, x, y, u, pick) => {
  if (u <= 0) return; const s = K.ease.back(K.clamp(u, 0, 1)); c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.translate(x + 300, y + 110); c.scale(s, s); c.rotate(-.03); c.translate(-300, -110);
  c.fillStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.roundRect(8, 14, 600, 220, 36); c.fill();
  c.fillStyle = '#ffffff'; c.beginPath(); c.roundRect(0, 0, 600, 220, 36); c.fill();
  const opt = (ox, lab, col, on) => { c.fillStyle = on ? col : '#eef0f5'; c.beginPath(); c.roundRect(ox, 40, 250, 140, 28); c.fill();
    c.fillStyle = on ? '#fff' : '#1d2133'; c.font = '900 72px "Inter Display", Inter, sans-serif'; c.textBaseline = 'middle'; c.textAlign = 'center'; c.fillText(lab, ox + 125, 112); };
  opt(32, 'YES', '#2bb673', pick === 1); opt(318, 'NO', '#ff4a3d', pick === 2);
  c.restore();
  if (u >= 1) { K.boxes.push({ s: 'YES', x: x + 32, y: y + 40, w: 250, h: 140 }); K.boxes.push({ s: 'NO', x: x + 318, y: y + 40, w: 250, h: 140 }); }
};
window.K = K;
})();
