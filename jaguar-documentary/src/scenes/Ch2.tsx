import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from '../kit/Car';
import {Bg, ChapterCard, Fadein, Flash, IllusTag, Kicker, Rise, Rule, Scene, Serif, Streaks, Svg, useSec} from '../kit/Stage';
import {SARTHE} from '../kit/maps';
import {trackAt} from '../kit/Track';
import {C, SANS, SERIF} from '../theme';
import {clamp, ease, eio3, eo3, kf, lerp, prog} from '../kit/anim';

/* 66.4-69.4 : to prove its speed */
const Intro: React.FC = () => {
  const t = useSec();
  const x = lerp(-160, 160, t / 3.2);
  return (
    <AbsoluteFill>
      <Bg tone="green" glow={0.4} />
      <Svg>
        <rect x={0} y={760} width={1920} height={320} fill="#040605" />
        <Streaks t={t} y0={600} y1={1050} speed={3200} n={32} seed={21} color={C.goldLite} />
        <g transform={`translate(${x} ${Math.sin(t * 34) * 1.1})`}>
          <g transform="translate(130 365) scale(1.7)">
            <Car id="ctype" uid="c1" tint="#1f4b39" spin={t * 1500} />
          </g>
        </g>
      </Svg>
      <ChapterCard n="Two" title="Conquering Le Mans" len={3.0} sub="Jaguar sets out to prove its speed" />
      <Flash t={t} at={0} dur={0.25} peak={0.5} />
    </AbsoluteFill>
  );
};

const WINS = [
  {y: 1951, car: 'C-Type', at: 0.3, note: 'First Le Mans victory'},
  {y: 1953, car: 'C-Type', at: 4.85, note: 'Disc brakes win at Le Mans'},
  {y: 1955, car: 'D-Type', at: 8.9, note: ''},
  {y: 1956, car: 'D-Type', at: 9.7, note: ''},
  {y: 1957, car: 'D-Type', at: 10.5, note: 'Jaguars finish 1-2-3-4-6'},
];

/* 69.2-81.0 : circuit + victories */
const LeMans: React.FC = () => {
  const t = useSec(); // 0 at 69.2
  const draw = eio3(prog(t, 0.0, 2.2));
  const k = 1.12;
  const lap1 = trackAt(t * 0.085), lap2 = trackAt(t * 0.085 - 0.06), lap3 = trackAt(t * 0.085 - 0.13);
  const dots = [lap1, lap2, lap3];
  const hours = Math.round(ease(t, 0.7, 3.0, eo3) * 24);
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.4} gx={30} />
      <Svg>
        <defs>
          <pattern id="g2" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke={C.silver} strokeOpacity={0.06} />
          </pattern>
        </defs>
        <rect width={1920} height={1080} fill="url(#g2)" />
        <g transform={`translate(110 170) scale(${k})`}>
          <path d={SARTHE} fill="none" stroke={C.silver} strokeOpacity={0.25} strokeWidth={26} strokeLinejoin="round" />
          <path d={SARTHE} fill="none" stroke={C.ivory} strokeOpacity={0.9} strokeWidth={3} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
          {dots.map((d, i) => (
            <g key={i} transform={`translate(${d.x} ${d.y})`} opacity={draw > 0.95 ? 1 : 0}>
              <circle r={i === 0 ? 9 : 6} fill={i === 0 ? C.goldLite : C.green} stroke={C.ivory} strokeWidth={1.5} />
            </g>
          ))}
          {/* labels */}
          <text x={470} y={52} fill={C.ivoryDim} fontFamily={SANS} fontSize={14} letterSpacing={3} fontWeight={600} opacity={draw}>MULSANNE STRAIGHT</text>
          <text x={180} y={330} fill={C.ivoryDim} fontFamily={SANS} fontSize={14} letterSpacing={3} fontWeight={600} opacity={draw}>START / FINISH</text>
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 90}}>
        <Fadein t={t} at={0.2}>
          <Kicker>Circuit de la Sarthe · schematic</Kicker>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 130, top: 800}}>
        <div style={{display: 'flex', alignItems: 'baseline', gap: 18}}>
          <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 130, color: C.ivory, lineHeight: 1}}>{hours}</div>
          <Kicker color={C.ivoryDim} size={20}>hours · flat out</Kicker>
        </div>
      </div>
      {/* victory list */}
      <div style={{position: 'absolute', left: 1180, top: 190, width: 640}}>
        <Fadein t={t} at={0.6}>
          <Kicker>Jaguar victories</Kicker>
        </Fadein>
        <Rule t={t} at={0.8} w={640} color="rgba(195,161,90,0.4)" style={{margin: '16px 0 10px'}} />
        {WINS.map((w) => {
          const p = eo3(prog(t, w.at, w.at + 0.7));
          const fl = 1 - prog(t, w.at, w.at + 0.9);
          return (
            <div key={w.y} style={{display: 'flex', alignItems: 'baseline', gap: 30, height: 112, borderBottom: '1px solid rgba(241,233,214,0.12)', opacity: 0.18 + 0.82 * p, transform: `translateX(${(1 - p) * 40}px)`}}>
              <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 96, color: p > 0.5 ? C.goldLite : C.ivoryDim, width: 220, textShadow: `0 0 ${fl * 30}px rgba(227,201,133,${fl})`}}>{w.y}</div>
              <div>
                <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 44, color: C.ivory}}>{w.car}</div>
                <Kicker size={13} color={C.ivoryDim} track={0.25}>{w.note || 'Winner'}</Kicker>
              </div>
            </div>
          );
        })}
      </div>
      <Fadein t={t} at={10.6} dur={0.8} style={{position: 'absolute', left: 130, bottom: 230}}>
        <Serif size={50} italic color={C.ivoryDim}>Five wins in seven years</Serif>
      </Fadein>
      {WINS.map((w) => (
        <Flash key={w.y} t={t} at={w.at} dur={0.3} peak={0.3} />
      ))}
    </AbsoluteFill>
  );
};

/* rotating disc brake */
const Disc: React.FC<{cx: number; cy: number; r: number; rot: number; p: number}> = ({cx, cy, r, rot, p}) => (
  <g opacity={p}>
    <circle cx={cx} cy={cy} r={r} fill="#0b0e0f" stroke={C.silverLite} strokeWidth={3} />
    <circle cx={cx} cy={cy} r={r * 0.62} fill="none" stroke={C.silver} strokeOpacity={0.5} strokeWidth={2} />
    <g transform={`rotate(${rot} ${cx} ${cy})`}>
      {Array.from({length: 24}).map((_, i) => {
        const a = (i / 24) * Math.PI * 2;
        return <circle key={i} cx={cx + Math.cos(a) * r * 0.8} cy={cy + Math.sin(a) * r * 0.8} r={r * 0.045} fill="#000" stroke={C.silver} strokeOpacity={0.6} />;
      })}
      <circle cx={cx} cy={cy} r={r * 0.24} fill="#1a1f20" stroke={C.gold} strokeWidth={2} />
    </g>
    <path d={`M ${cx + r * 0.55} ${cy - r * 0.55} A ${r * 0.78} ${r * 0.78} 0 0 1 ${cx + r * 0.78} ${cy + r * 0.1}`} fill="none" stroke={C.gold} strokeWidth={r * 0.2} strokeLinecap="round" opacity={0.85} />
  </g>
);

/* 81.0-88.6 : D-Type technology */
const DType: React.FC = () => {
  const t = useSec(); // 0 at 81.0
  const draw = eio3(prog(t, 0.2, 2.2));
  const fill = eo3(prog(t, 1.5, 2.8));
  const flow = eo3(prog(t, 3.3, 4.3));
  const brake = eo3(prog(t, 4.4, 5.2));
  const lines = [-70, -44, -20, 6, 32];
  return (
    <AbsoluteFill>
      <Bg tone="cold" glow={0.4} gx={40} />
      <Svg>
        <g transform="translate(90 340) scale(1.5)">
          <Car id="dtype" uid="dt" draw={draw} fill={fill} spin={t * 800} tint="#1f4b39" />
          {lines.map((dy, i) => {
            const D = `M -60,${150 + dy * 0.2} C 120,${150 + dy * 0.2} 170,${40 + dy} 330,${52 + dy} C 480,${60 + dy} 600,${96 + dy * 0.9} 720,${108 + dy * 0.8} C 840,${120 + dy * 0.6} 980,${134 + dy * 0.4} 1120,${138 + dy * 0.3}`;
            return <path key={i} d={D} fill="none" stroke={C.goldLite} strokeWidth={1.8} strokeOpacity={0.75 * flow} strokeDasharray="14 22" strokeDashoffset={-t * 260} />;
          })}
        </g>
        <Disc cx={1480} cy={730} r={170} rot={t * 380} p={brake} />
        <line x1={1296} y1={730} x2={1040} y2={640} stroke={C.gold} strokeOpacity={0.7 * brake} />
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 130}}>
        <Fadein t={t} at={0.2}>
          <Kicker>1954–57 · Le Mans winner</Kicker>
        </Fadein>
        <Rule t={t} at={0.3} w={110} style={{margin: '16px 0'}} />
        <Rise t={t} at={0.4} dur={0.9}>
          <Serif size={130}>D-Type</Serif>
        </Rise>
      </div>
      <div style={{position: 'absolute', left: 1020, top: 150, width: 640, opacity: flow}}>
        <Kicker size={18}>Aerodynamics</Kicker>
        <Serif size={44} italic style={{marginTop: 8}}>Shaped by the wind, tail fin and all</Serif>
      </div>
      <div style={{position: 'absolute', left: 880, top: 800, width: 420, opacity: brake}}>
        <Kicker size={18}>Disc brakes</Kicker>
        <Serif size={44} italic style={{marginTop: 8}}>Proven under brutal racing conditions</Serif>
      </div>
      <IllusTag text="Original technical illustration" />
    </AbsoluteFill>
  );
};

/* 88.6-91.6 : reputation */
const Reputation: React.FC = () => {
  const t = useSec(); // 0 at 88.6
  const pos = [1, 2, 3, 4, 6];
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.45} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 250, textAlign: 'center'}}>
        <Fadein t={t} at={0.0} dur={0.8}>
          <Kicker size={22}>Le Mans · 1957</Kicker>
        </Fadein>
        <div style={{display: 'flex', justifyContent: 'center', gap: 36, marginTop: 40}}>
          {pos.map((p, i) => {
            const a = eo3(prog(t, 0.3 + i * 0.18, 0.8 + i * 0.18));
            return (
              <div key={p} style={{width: 150, height: 200, border: `1.5px solid ${C.gold}`, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: a, transform: `translateY(${(1 - a) * 30}px)`, fontFamily: SERIF, fontWeight: 600, fontSize: 120, color: C.ivory}}>
                {p}
                <span style={{fontSize: 40, color: C.gold, marginLeft: 4, alignSelf: 'flex-start', marginTop: 28}}>{p === 1 ? 'st' : p === 2 ? 'nd' : p === 3 ? 'rd' : 'th'}</span>
              </div>
            );
          })}
        </div>
        <Fadein t={t} at={1.5} dur={0.9}>
          <Serif size={62} italic style={{marginTop: 50}}>A reputation money couldn't buy</Serif>
        </Fadein>
      </div>
    </AbsoluteFill>
  );
};

export const Ch2: React.FC = () => (
  <>
    <Scene from={66.4} to={69.4} fi={0.2} fo={0.2}>
      <Intro />
    </Scene>
    <Scene from={69.2} to={81.2} fi={0.2} fo={0.2}>
      <LeMans />
    </Scene>
    <Scene from={81.0} to={88.8} fi={0.2} fo={0.25}>
      <DType />
    </Scene>
    <Scene from={88.6} to={91.6} fi={0.25} fo={0.2}>
      <Reputation />
    </Scene>
  </>
);
