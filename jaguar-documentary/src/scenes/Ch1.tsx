import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from '../kit/Car';
import {Bg, ChapterCard, Fadein, Flash, IllusTag, Kicker, Rise, Rule, Scene, Serif, Svg, useSec} from '../kit/Stage';
import {Gauge} from '../kit/Gauge';
import {BLACKPOOL, COVENTRY, gbPath, projGB} from '../kit/maps';
import {C, SANS, SERIF} from '../theme';
import {clamp, ease, eio3, eo3, kf, lerp, prog} from '../kit/anim';

/* 28.7-35.2 : 1922 */
const Origin: React.FC = () => {
  const t = useSec();
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.45} gx={30} />
      <div style={{position: 'absolute', left: 150, top: 150, fontFamily: SERIF, fontWeight: 600, fontSize: 380, color: C.ivory, lineHeight: 1, opacity: 0.96, transform: `scale(${1 + t * 0.006})`, transformOrigin: 'left top'}}>1922</div>
      <div style={{position: 'absolute', left: 1050, top: 330, width: 700}}>
        <Fadein t={t} at={1.6}>
          <Kicker>Swallow Sidecar Company</Kicker>
        </Fadein>
        <Rule t={t} at={1.8} w={120} style={{margin: '18px 0 22px'}} />
        <Rise t={t} at={2.0} dur={0.9}>
          <Serif size={72}>William Lyons</Serif>
        </Rise>
        <Rise t={t} at={2.5} dur={0.9}>
          <Serif size={72} italic color={C.ivoryDim}>& William Walmsley</Serif>
        </Rise>
        <Fadein t={t} at={4.5} dur={0.9}>
          <Kicker color={C.ivoryDim} size={20} track={0.3} style={{marginTop: 28}}>motorcycle sidecars · Blackpool</Kicker>
        </Fadein>
      </div>
      <Sheen t={t} />
      <ChapterCard n="One" title="The Birth of a Legend" len={3.4} />
    </AbsoluteFill>
  );
};
const Sheen: React.FC<{t: number}> = ({t}) => (
  <div style={{position: 'absolute', inset: 0, background: `linear-gradient(100deg, rgba(255,240,205,0) ${(t * 22) % 140 - 20}%, rgba(255,240,205,0.05) ${(t * 22) % 140}%, rgba(255,240,205,0) ${(t * 22) % 140 + 20}%)`, mixBlendMode: 'screen'}} />
);

/* 35.2-41.6 : map */
const MapScene: React.FC = () => {
  const t = useSec(); // 0 at 35.2
  const bp = projGB(...BLACKPOOL), cv = projGB(...COVENTRY);
  const draw = eo3(prog(t, 0.0, 1.8));
  const route = eio3(prog(t, 3.0, 4.6));
  const midx = lerp(bp[0], cv[0], route), midy = lerp(bp[1], cv[1], route);
  const pin = (x: number, y: number, p: number, label: string, sub: string, left = false) => (
    <g opacity={p}>
      <circle cx={x} cy={y} r={7 + (1 - p) * 20} fill={C.gold} />
      <circle cx={x} cy={y} r={20 + 6 * Math.sin(t * 4)} fill="none" stroke={C.gold} strokeOpacity={0.6} />
      <line x1={x} y1={y} x2={x + (left ? -90 : 90)} y2={y - 40} stroke={C.gold} strokeOpacity={0.7} />
    </g>
  );
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.4} gx={72} />
      <Svg>
        <defs>
          <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke={C.silver} strokeOpacity={0.07} />
          </pattern>
        </defs>
        <rect width={1920} height={1080} fill="url(#grid)" />
        <path d={gbPath()} fill={C.green} fillOpacity={0.35 * draw} stroke={C.silverLite} strokeOpacity={0.9} strokeWidth={2} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
        <path d={`M ${bp[0]},${bp[1]} L ${midx},${midy}`} stroke={C.goldLite} strokeWidth={3} strokeDasharray="10 8" fill="none" />
        {pin(bp[0], bp[1], eo3(prog(t, 1.4, 2.0)), 'Blackpool', '1922')}
        {pin(cv[0], cv[1], eo3(prog(t, 4.4, 5.0)), 'Coventry', '1928', true)}
      </Svg>
      <div style={{position: 'absolute', left: bp[0] - 420, top: bp[1] - 40, textAlign: 'right', width: 380, opacity: eo3(prog(t, 1.7, 2.3))}}>
        <Serif size={44}>Blackpool</Serif>
        <Kicker size={15} color={C.ivoryDim} track={0.3}>1922 · swallow sidecars</Kicker>
      </div>
      <div style={{position: 'absolute', left: cv[0] - 470, top: cv[1] - 30, textAlign: 'right', width: 420, opacity: eo3(prog(t, 4.6, 5.2))}}>
        <Serif size={44}>Coventry</Serif>
        <Kicker size={15} color={C.ivoryDim} track={0.3}>1928 · the company moves</Kicker>
      </div>
      <div style={{position: 'absolute', left: 130, top: 300, width: 760}}>
        <Fadein t={t} at={0.3}>
          <Kicker>Where it began</Kicker>
        </Fadein>
        <Rule t={t} at={0.5} w={120} style={{margin: '18px 0 22px'}} />
        <Rise t={t} at={0.6} dur={1.0}>
          <Serif size={92}>A sidecar maker on the Lancashire coast</Serif>
        </Rise>
        <Fadein t={t} at={3.2} dur={1.0}>
          <Serif size={50} italic color={C.ivoryDim} style={{marginTop: 28}}>…becomes a luxury empire in the Midlands</Serif>
        </Fadein>
      </div>
      <Kicker color="rgba(241,233,214,0.35)" size={13} track={0.3} style={{position: 'absolute', right: 70, bottom: 52}}>schematic map · not to scale</Kicker>
    </AbsoluteFill>
  );
};

/* 41.0-58.9 : timeline */
const Timeline: React.FC = () => {
  const t = useSec(); // 0 at 41.0
  const X = (y: number) => 200 + ((y - 1920) / 30) * 1520;
  const nodes = [
    {y: 1922, at: 0.2, up: false, a: 'Swallow Sidecar Co.', b: 'Blackpool'},
    {y: 1928, at: 0.9, up: true, a: 'Moves to Coventry', b: 'Car bodies for others'},
    {y: 1935, at: 2.5, up: false, a: 'SS Jaguar', b: 'The first car to wear the name'},
    {y: 1945, at: 10.1, up: true, a: 'Jaguar Cars Ltd', b: '“SS” dropped after the war'},
    {y: 1948, at: 14.5, up: false, a: 'XK120', b: 'Everything changed'},
  ];
  const lineP = eio3(prog(t, 0.0, 16.0));
  const words = [['Stylish', 5.8], ['Powerful', 6.7], ['Affordable', 8.2]] as const;
  const camX = kf(t, [[0, 0], [16, -40]]);
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.4} />
      <Svg>
        <g transform={`translate(${camX} 0)`}>
          <line x1={X(1920) - 60} y1={640} x2={lerp(X(1920) - 60, X(1950) + 40, lineP)} y2={640} stroke={C.ivory} strokeOpacity={0.55} strokeWidth={2} />
          {Array.from({length: 31}).map((_, i) => {
            const x = X(1920 + i);
            return x < lerp(X(1920) - 60, X(1950) + 40, lineP) ? <line key={i} x1={x} x2={x} y1={640} y2={i % 5 === 0 ? 660 : 652} stroke={C.ivory} strokeOpacity={0.4} /> : null;
          })}
          {nodes.map((n) => {
            const p = eo3(prog(t, n.at, n.at + 0.7));
            const x = X(n.y);
            return (
              <g key={n.y} opacity={p}>
                <line x1={x} x2={x} y1={640} y2={n.up ? 640 - 90 * p : 640 + 90 * p} stroke={C.gold} strokeWidth={2} />
                <circle cx={x} cy={640} r={12 * (0.4 + 0.6 * p)} fill={C.char} stroke={C.gold} strokeWidth={3} />
              </g>
            );
          })}
        </g>
      </Svg>
      {nodes.map((n) => {
        const x = X(n.y) + camX;
        const p = eo3(prog(t, n.at + 0.3, n.at + 1.1));
        return (
          <div key={n.y} style={{position: 'absolute', left: x - 200, width: 400, textAlign: 'center', top: n.up ? 330 : 770, opacity: p, transform: `translateY(${(1 - p) * (n.up ? -14 : 14)}px)`}}>
            <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 68, color: C.goldLite, lineHeight: 1}}>{n.y}</div>
            <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 40, color: C.ivory, marginTop: 8}}>{n.a}</div>
            <Kicker size={14} color={C.ivoryDim} track={0.25} style={{marginTop: 8}}>{n.b}</Kicker>
          </div>
        );
      })}
      <div style={{position: 'absolute', left: 0, right: 0, top: 120, textAlign: 'center'}}>
        <Fadein t={t} at={0.1}>
          <Kicker>A company finds its name</Kicker>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 560, top: 210, display: 'flex', gap: 46, fontFamily: SERIF, fontStyle: 'italic', fontSize: 64, color: C.ivory}}>
        {words.map(([w, at]) => (
          <span key={w} style={{opacity: eo3(prog(t, at, at + 0.6)), transform: `translateY(${(1 - eo3(prog(t, at, at + 0.6))) * 24}px)`}}>
            {w}
            {w !== 'Affordable' && <span style={{color: C.gold}}>{'  ·'}</span>}
          </span>
        ))}
      </div>
      <Flash t={t} at={14.5} dur={0.3} peak={0.35} />
    </AbsoluteFill>
  );
};

/* 58.8-66.4 : XK120 */
const XK: React.FC = () => {
  const t = useSec(); // 0 at 58.8
  const draw = eio3(prog(t, 0.2, 2.6));
  const fill = eo3(prog(t, 1.8, 3.2));
  const speed = ease(t, 3.2, 5.4, eio3) * 120;
  const s = lerp(1.0, 1.06, t / 7.6);
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.35} gx={40} gy={55} />
      <Svg>
        <g transform={`translate(${960 - 960 * s} ${540 - 540 * s}) scale(${s})`}>
          <g transform="translate(30 400) scale(1.4)">
            <Car id="xk120" uid="xk" draw={draw} fill={fill} tint="#2a4a5a" spin={t * 200} rim={C.silverLite} />
          </g>
        </g>
        <g opacity={eo3(prog(t, 3.0, 3.8))}>
          <Gauge cx={1560} cy={300} r={150} value={speed} max={140} major={20} label="MPH" readout={String(Math.round(speed))} unit="XK120 · 1948" red={120} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 140}}>
        <Fadein t={t} at={0.2}>
          <Kicker>1948 · London Motor Show</Kicker>
        </Fadein>
        <Rule t={t} at={0.3} w={110} style={{margin: '16px 0'}} />
        <Rise t={t} at={0.4} dur={0.9}>
          <Serif size={150}>XK120</Serif>
        </Rise>
        <Fadein t={t} at={4.6}>
          <Kicker size={18} color={C.ivoryDim} track={0.28}>Flowing bodywork · 3.4-litre straight-six</Kicker>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 130, bottom: 120}}>
        <Fadein t={t} at={4.5} dur={0.9}>
          <Serif size={56} italic>One of the fastest production cars in the world</Serif>
        </Fadein>
      </div>
      <IllusTag />
      <Flash t={t} at={0.1} dur={0.3} peak={0.5} />
    </AbsoluteFill>
  );
};

export const Ch1: React.FC = () => (
  <>
    <Scene from={28.7} to={35.3} fi={0.1} fo={0.3}>
      <Origin />
    </Scene>
    <Scene from={35.2} to={41.4} fi={0.3} fo={0.3}>
      <MapScene />
    </Scene>
    <Scene from={41.0} to={59.0} fi={0.3} fo={0.3}>
      <Timeline />
    </Scene>
    <Scene from={58.8} to={66.6} fi={0.1} fo={0.4}>
      <XK />
    </Scene>
  </>
);
