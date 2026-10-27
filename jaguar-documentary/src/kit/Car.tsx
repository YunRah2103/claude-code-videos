import React from 'react';
import {CARS} from './carData';
import {C} from '../theme';

type Props = {
  id: keyof typeof CARS | string;
  x?: number;
  y?: number;
  scale?: number;
  spin?: number; // wheel rotation deg
  draw?: number; // 0..1 outline draw-on progress
  fill?: number; // 0..1 fill reveal
  tint?: string; // body base colour
  rim?: string; // outline colour
  ground?: boolean;
  lamp?: number; // headlamp glow 0..1
  uid?: string;
};

const Wheel: React.FC<{x: number; y: number; r: number; spin: number; wire?: boolean; rim: string}> = ({x, y, r, spin, wire, rim}) => {
  const spokes = wire ? 24 : 5;
  return (
    <g transform={`translate(${x} ${y})`}>
      <circle r={r} fill="#07090a" stroke="#000" strokeWidth={2} />
      <circle r={r - 7} fill="none" stroke="#1d2123" strokeWidth={3} />
      <circle r={r * 0.66} fill="#12171a" stroke={rim} strokeOpacity={0.65} strokeWidth={2.5} />
      <g transform={`rotate(${spin})`} stroke={wire ? '#cfd5d8' : '#9aa2a6'} strokeOpacity={wire ? 0.5 : 0.9} strokeWidth={wire ? 0.9 : 6} strokeLinecap="round">
        {Array.from({length: spokes}).map((_, i) => {
          const a = (i / spokes) * Math.PI * 2;
          return <line key={i} x1={Math.cos(a) * r * 0.1} y1={Math.sin(a) * r * 0.1} x2={Math.cos(a) * r * 0.64} y2={Math.sin(a) * r * 0.64} />;
        })}
      </g>
      <circle r={r * 0.1} fill={C.gold} />
    </g>
  );
};

export const Car: React.FC<Props> = ({id, x = 0, y = 0, scale = 1, spin = 0, draw = 1, fill = 1, tint = '#173b2e', rim = C.silverLite, ground = true, lamp = 0, uid = 'a'}) => {
  const car = CARS[id as string];
  const gid = `${car.id}-${uid}`;
  const L = 4200;
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <defs>
        <linearGradient id={`bg-${gid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5d7d70" />
          <stop offset="0.28" stopColor={tint} />
          <stop offset="0.75" stopColor="#0a1a14" />
          <stop offset="1" stopColor="#050a08" />
        </linearGradient>
        <linearGradient id={`sheen-${gid}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity="0" />
          <stop offset="0.35" stopColor="#fff" stopOpacity="0.16" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0" />
          <stop offset="0.85" stopColor="#fff" stopOpacity="0.1" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id={`gl-${gid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8fa6ae" stopOpacity="0.55" />
          <stop offset="1" stopColor="#0a1114" stopOpacity="0.95" />
        </linearGradient>
        <radialGradient id={`sh-${gid}`}>
          <stop offset="0" stopColor="#000" stopOpacity="0.85" />
          <stop offset="1" stopColor="#000" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`lp-${gid}`}>
          <stop offset="0" stopColor="#fff6d8" stopOpacity="0.95" />
          <stop offset="1" stopColor="#fff6d8" stopOpacity="0" />
        </radialGradient>
        <mask id={`m-${gid}`}>
          <rect x="-50" y="-50" width="1100" height="400" fill="#fff" />
          {car.wheels.map((w, i) => (
            <circle key={i} cx={w.x} cy={w.y} r={car.arch} fill="#000" />
          ))}
        </mask>
        <clipPath id={`gc-${gid}`}>
          <path d={car.body} />
        </clipPath>
      </defs>
      {ground && <ellipse cx={500} cy={262} rx={470} ry={16} fill={`url(#sh-${gid})`} />}
      {car.wheels.map((w, i) => (
        <Wheel key={i} x={w.x} y={w.y} r={w.r} spin={spin} wire={car.wire} rim={rim} />
      ))}
      <g mask={`url(#m-${gid})`}>
        <path d={car.body} fill={`url(#bg-${gid})`} opacity={fill} />
        <g clipPath={`url(#gc-${gid})`} opacity={fill}>
          <rect x="0" y="0" width="1000" height="300" fill={`url(#sheen-${gid})`} />
          <path d={car.lines[car.lines.length > 2 ? 2 : 0]} stroke="#fff" strokeOpacity={0.22} strokeWidth={5} fill="none" />
        </g>
        <path d={car.glass} fill={`url(#gl-${gid})`} opacity={fill} />
        <path d={car.body} fill="none" stroke={rim} strokeWidth={2.4} strokeLinejoin="round" strokeDasharray={L} strokeDashoffset={L * (1 - draw)} />
        {car.lines.map((d, i) => (
          <path key={i} d={d} fill="none" stroke={rim} strokeOpacity={0.4} strokeWidth={1.3} strokeDasharray={L} strokeDashoffset={L * (1 - draw)} />
        ))}
        <path d={car.glass} fill="none" stroke={rim} strokeOpacity={0.7} strokeWidth={1.6} strokeDasharray={L} strokeDashoffset={L * (1 - draw)} />
      </g>
      {car.accent?.map((d, i) => (
        <path key={i} d={d} stroke={C.goldLite} strokeWidth={2.4} fill="none" opacity={fill} />
      ))}
      {car.lamps.map((l, i) => (
        <g key={i} transform={`translate(${l.x} ${l.y}) rotate(${l.rot ?? 0})`} opacity={fill}>
          <ellipse rx={l.rx} ry={l.ry} fill="#0a1114" stroke={C.silverLite} strokeWidth={1.8} />
          <ellipse rx={l.rx * 0.55} ry={l.ry * 0.55} fill={lamp > 0 ? '#fff4d0' : '#8a979c'} fillOpacity={lamp > 0 ? 0.6 + lamp * 0.4 : 0.5} />
          {lamp > 0 && <ellipse rx={l.rx * 5} ry={l.ry * 4} fill={`url(#lp-${gid})`} opacity={lamp * 0.45} />}
        </g>
      ))}
    </g>
  );
};
