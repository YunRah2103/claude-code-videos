import React from 'react';
import {C, SANS, SERIF} from '../theme';

/** Instrument dial: value 0..max sweeping over 270 degrees. */
export const Gauge: React.FC<{cx: number; cy: number; r: number; value: number; max: number; major: number; label?: string; unit?: string; readout?: string; color?: string; red?: number}> = ({cx, cy, r, value, max, major, label, unit, readout, color = C.ivory, red}) => {
  const a0 = 135, sweep = 270;
  const ang = (v: number) => ((a0 + (v / max) * sweep) * Math.PI) / 180;
  const pt = (v: number, rad: number) => [cx + Math.cos(ang(v)) * rad, cy + Math.sin(ang(v)) * rad];
  const arc = (v0: number, v1: number, rad: number) => {
    const [x0, y0] = pt(v0, rad), [x1, y1] = pt(v1, rad);
    return `M ${x0} ${y0} A ${rad} ${rad} 0 ${(v1 - v0) / max * sweep > 180 ? 1 : 0} 1 ${x1} ${y1}`;
  };
  const ticks = [];
  for (let v = 0; v <= max + 0.001; v += major / 4) {
    const isMajor = Math.abs(v / major - Math.round(v / major)) < 0.001;
    const [x0, y0] = pt(v, r - (isMajor ? 22 : 12)), [x1, y1] = pt(v, r - 2);
    ticks.push(<line key={v} x1={x0} y1={y0} x2={x1} y2={y1} stroke={red !== undefined && v >= red ? C.redLite : color} strokeWidth={isMajor ? 3 : 1.4} strokeOpacity={isMajor ? 0.95 : 0.5} />);
    if (isMajor) {
      const [tx, ty] = pt(v, r - 46);
      ticks.push(
        <text key={'t' + v} x={tx} y={ty + 8} textAnchor="middle" fontFamily={SANS} fontWeight={500} fontSize={r * 0.13} fill={color} fillOpacity={0.8}>
          {Math.round(v)}
        </text>
      );
    }
  }
  const [nx, ny] = pt(value, r - 30);
  const [bx, by] = pt(value + max / 2, 18);
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill="#07090a" fillOpacity={0.8} stroke={C.silver} strokeOpacity={0.7} strokeWidth={3} />
      <circle cx={cx} cy={cy} r={r - 8} fill="none" stroke={C.gold} strokeOpacity={0.35} strokeWidth={1} />
      <path d={arc(0, Math.max(0.001, Math.min(value, max)), r - 10)} fill="none" stroke={C.gold} strokeWidth={4} strokeOpacity={0.9} />
      {ticks}
      {label && (
        <text x={cx} y={cy - r * 0.32} textAnchor="middle" fontFamily={SANS} fontWeight={600} fontSize={r * 0.085} letterSpacing={r * 0.03} fill={C.gold}>
          {label}
        </text>
      )}
      {readout && (
        <text x={cx} y={cy + r * 0.5} textAnchor="middle" fontFamily={SERIF} fontWeight={600} fontSize={r * 0.3} fill={C.ivory}>
          {readout}
        </text>
      )}
      {unit && (
        <text x={cx} y={cy + r * 0.64} textAnchor="middle" fontFamily={SANS} fontWeight={500} fontSize={r * 0.08} letterSpacing={r * 0.03} fill={C.ivoryDim}>
          {unit}
        </text>
      )}
      <line x1={bx} y1={by + cy - cy} x2={nx} y2={ny} stroke={C.redLite} strokeWidth={4} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={11} fill={C.silverLite} />
    </g>
  );
};
