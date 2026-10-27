import {SARTHE} from './maps';
let cache: {x: number; y: number}[] | null = null;
let total = 0;
/** Sample the circuit path once (browser only). */
export const trackPoints = () => {
  if (cache) return cache;
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  p.setAttribute('d', SARTHE);
  total = p.getTotalLength();
  cache = Array.from({length: 721}).map((_, i) => {
    const pt = p.getPointAtLength((i / 720) * total);
    return {x: pt.x, y: pt.y};
  });
  return cache;
};
export const trackAt = (u: number) => {
  const pts = trackPoints();
  const f = (((u % 1) + 1) % 1) * 720;
  const i = Math.floor(f), r = f - i;
  const a = pts[i], b = pts[i + 1];
  return {x: a.x + (b.x - a.x) * r, y: a.y + (b.y - a.y) * r, ang: (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI};
};
