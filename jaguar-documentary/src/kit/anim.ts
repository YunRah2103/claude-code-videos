export const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const prog = (t: number, a: number, b: number) => clamp((t - a) / (b - a));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const eo3 = (x: number) => 1 - Math.pow(1 - x, 3);
export const eo5 = (x: number) => 1 - Math.pow(1 - x, 5);
export const ei3 = (x: number) => x * x * x;
export const eio3 = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const eio2 = (x: number) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
export const eoBack = (x: number) => {
  const c1 = 1.4, c3 = c1 + 1;
  return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
};
/** ease helper: progress of t between a..b through easing fn */
export const ease = (t: number, a: number, b: number, fn: (x: number) => number = eo3) => fn(prog(t, a, b));
export const rnd = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
/** keyframe interpolation: kf(t, [[t0,v0],[t1,v1],...], easingFn) */
export const kf = (t: number, pts: [number, number][], fn: (x: number) => number = (x) => x * x * (3 - 2 * x)) => {
  if (t <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i++) {
    if (t <= pts[i][0]) {
      const [a, va] = pts[i - 1], [b, vb] = pts[i];
      return va + (vb - va) * fn((t - a) / (b - a));
    }
  }
  return pts[pts.length - 1][1];
};
