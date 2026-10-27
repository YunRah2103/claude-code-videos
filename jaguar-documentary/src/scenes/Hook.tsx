import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from '../kit/Car';
import {Bg, Finish, Flash, IllusTag, Kicker, Rise, Fadein, Rule, Scene, Serif, Streaks, Svg, useSec} from '../kit/Stage';
import {Gauge} from '../kit/Gauge';
import {C, SANS, SERIF} from '../theme';
import {clamp, eio3, eo3, kf, lerp, prog, rnd, ease} from '../kit/anim';

/** Camera on an 1000x300 car box: focus point (fx,fy) at screen centre, uniform scale s, placed at ox,oy. */
const camXf = (fx: number, fy: number, s: number, cx = 960, cy = 560) => `translate(${cx - fx * s} ${cy - fy * s}) scale(${s})`;

const Sweep: React.FC<{p: number; opacity?: number}> = ({p, opacity = 0.35}) => (
  <div style={{position: 'absolute', inset: 0, overflow: 'hidden', mixBlendMode: 'screen', pointerEvents: 'none'}}>
    <div style={{position: 'absolute', top: -200, left: `${-30 + p * 160}%`, width: '14%', height: '150%', transform: 'rotate(18deg)', background: `linear-gradient(90deg, rgba(255,240,205,0), rgba(255,240,205,${opacity}), rgba(255,240,205,0))`}} />
  </div>
);

/* 0.0-4.4 : E-Type hero */
const HeroEType: React.FC = () => {
  const t = useSec();
  const s = kf(t, [[0, 5.0], [1.5, 4.2], [1.5, 3.2], [3.0, 2.7], [3.0, 2.7], [4.4, 1.75]], eio3);
  const fx = kf(t, [[0, 915], [1.5, 905], [1.5, 880], [3.0, 560], [4.4, 520]], eio3);
  const fy = kf(t, [[0, 168], [1.5, 160], [1.5, 120], [3.0, 110], [4.4, 150]], eio3);
  const lamp = clamp(prog(t, 0.45, 0.7));
  const wob = Math.sin(t * 40) * (t < 2 ? 1.6 : 0.5);
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.3} gy={55} />
      <Svg>
        <rect x={0} y={800} width={1920} height={280} fill="url(#floor)" />
        <defs>
          <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#1a1f1e" />
            <stop offset="1" stopColor="#030404" />
          </linearGradient>
        </defs>
        <g transform={`translate(0 ${wob})`}>
          <g transform={camXf(fx, fy, s)}>
            <Car id="etype" uid="hero" lamp={lamp} spin={t * 900} tint="#1d4636" ground />
          </g>
        </g>
      </Svg>
      <Sweep p={prog(t, 0.2, 3.6)} opacity={0.3} />
      <Flash t={t} at={0.45} dur={0.35} peak={0.8} />
      <Flash t={t} at={1.5} dur={0.18} peak={0.55} />
      <Flash t={t} at={3.0} dur={0.18} peak={0.55} />
    </AbsoluteFill>
  );
};

/* generic racing pass */
const Pass: React.FC<{id: string; label: string; sub: string; dir?: 1 | -1; s?: number; tint?: string; dur: number; seed: number; fy?: number}> = ({id, label, sub, dir = 1, s = 1.9, tint, dur, seed, fy = 150}) => {
  const t = useSec();
  const p = t / dur;
  const x = lerp(-120 * dir, 120 * dir, p);
  const bob = Math.sin(t * 38 + seed) * 1.2;
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.2} gy={60} />
      <Svg>
        <rect x={0} y={760} width={1920} height={320} fill="#050606" />
        <line x1={0} y1={760} x2={1920} y2={760} stroke={C.silver} strokeOpacity={0.3} />
        <Streaks t={t} y0={620} y1={1060} speed={3600} n={34} seed={seed} />
        <Streaks t={t} y0={120} y1={560} speed={1200} n={10} seed={seed + 40} color={C.gold} />
        <g transform={`translate(${x} ${bob})`}>
          <g transform={`translate(${960 - 500 * s * 0.98} ${770 - 262 * s}) scale(${s})`}>
            <Car id={id} uid={'p' + seed} spin={t * 1400} tint={tint} />
          </g>
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 110, bottom: 120}}>
        <Fadein t={t} at={0.15} dur={0.4}>
          <Kicker size={20}>{sub}</Kicker>
        </Fadein>
        <Rise t={t} at={0.1} dur={0.5}>
          <Serif size={72}>{label}</Serif>
        </Rise>
      </div>
      <Flash t={t} at={0} dur={0.2} peak={0.5} />
    </AbsoluteFill>
  );
};

/* Le Mans plaque, 7.6-8.8 */
const LeMansBeat: React.FC = () => {
  const t = useSec();
  const years = [1951, 1953, 1955, 1956, 1957];
  return (
    <AbsoluteFill>
      <Bg tone="green" glow={0.4} />
      <Svg>
        <Streaks t={t} y0={300} y1={800} speed={2800} n={30} seed={3} color={C.goldLite} />
        <g transform="translate(960 540)">
          <circle r={250} fill="none" stroke={C.gold} strokeOpacity={0.5} strokeWidth={1.5} />
          <circle r={236} fill="none" stroke={C.gold} strokeOpacity={0.25} strokeWidth={1} strokeDasharray="2 8" />
        </g>
      </Svg>
      <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <Fadein t={t} at={0.0} dur={0.3}>
          <Kicker size={24}>24 hours of le mans</Kicker>
        </Fadein>
        <div style={{display: 'flex', gap: 34, marginTop: 20}}>
          {years.map((y, i) => {
            const p = eo3(prog(t, 0.1 + i * 0.17, 0.35 + i * 0.17));
            return (
              <div key={y} style={{fontFamily: SERIF, fontWeight: 600, fontSize: 88, color: C.ivory, opacity: p, transform: `scale(${1.25 - 0.25 * p})`}}>
                {y}
              </div>
            );
          })}
        </div>
        <Fadein t={t} at={0.9} dur={0.3}>
          <Kicker size={18} color={C.ivoryDim}>five victories</Kicker>
        </Fadein>
      </div>
      {years.map((y, i) => (
        <Flash key={y} t={t} at={0.1 + i * 0.17} dur={0.12} peak={0.25} />
      ))}
    </AbsoluteFill>
  );
};

/* 9.7-13.4 elegance */
const Elegance: React.FC = () => {
  const t = useSec();
  const s = lerp(1.15, 1.32, t / 3.7);
  const fx = lerp(560, 470, t / 3.7);
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.5} gy={45} />
      <Svg>
        <g transform={camXf(fx, 140, s, 960, 520)}>
          <Car id="etype" uid="eleg" spin={0} tint="#1f4b39" rim={C.goldLite} lamp={0.6} />
        </g>
      </Svg>
      <Sweep p={prog(t, 0.2, 3.4)} opacity={0.18} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 150, textAlign: 'center'}}>
        <Fadein t={t} at={0.2} dur={1.0}>
          <Kicker size={22} track={0.55}>british elegance</Kicker>
        </Fadein>
        <Rule t={t} at={0.5} w={140} style={{margin: '18px auto'}} />
        <Fadein t={t} at={2.0} dur={0.9}>
          <Serif size={58} italic color={C.ivory}>with a dangerous edge</Serif>
        </Fadein>
      </div>
    </AbsoluteFill>
  );
};

/* 13.4-21 : the turn - engine stops */
const TheTurn: React.FC = () => {
  const t = useSec(); // 0 at 13.4
  const split = kf(t, [[0, 50], [0.9, 50], [2.2, 44]], eio3);
  const rpm = kf(t, [[0, 6.4], [0.1, 6.4], [2.0, 0.0]], eio3);
  const typeIn = eo3(prog(t, 5.0, 6.6));
  const eLeft = 1 - 0.55 * prog(t, 2.0, 4.0);
  return (
    <AbsoluteFill>
      <Bg tone="black" glow={0.2} />
      <AbsoluteFill style={{background: `radial-gradient(60% 40% at 78% 70%, rgba(179,38,43,${0.16 * typeIn}), rgba(0,0,0,0))`}} />
      <Svg>
        {/* divider */}
        <line x1={960} y1={140} x2={960} y2={940} stroke={C.silver} strokeOpacity={0.25} strokeDasharray="3 9" />
        {/* left: E-Type fading */}
        <g opacity={eLeft} transform="translate(20 330) scale(0.94)">
          <Car id="etype" uid="turnL" tint="#2b3a35" rim={C.silver} />
        </g>
        {/* tachometer winding down */}
        <g opacity={clamp(prog(t, 0.2, 0.6)) * (1 - 0.7 * prog(t, 4, 5))}>
          <Gauge cx={470} cy={235} r={105} value={rpm} max={8} major={1} label="RPM x1000" red={6.5} />
        </g>
        {/* right: Type 01 emerging */}
        <g opacity={typeIn} transform={`translate(${990 + (1 - typeIn) * 80} 330) scale(0.94)`}>
          <Car id="gt" uid="turnR" tint="#27302e" rim={C.goldLite} lamp={typeIn} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 120, top: 120}}>
        <Fadein t={t} at={0.4}>
          <Kicker color={C.ivoryDim} size={20}>1961 · E-Type</Kicker>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 1040, top: 120}}>
        <Fadein t={t} at={5.2}>
          <Kicker color={C.goldLite} size={20}>2026 · Type 01</Kicker>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 170, textAlign: 'center'}}>
        <Fadein t={t} at={0.5} dur={0.8}>
          <Serif size={64} italic color={C.ivory} style={{opacity: t < 3.2 ? 1 : 0.0}}>Today</Serif>
        </Fadein>
        <Fadein t={t} at={2.3} dur={0.8} style={{position: 'absolute', left: 0, right: 0, top: 0, opacity: t > 2.3 && t < 5.0 ? 1 : 0}}>
          <Kicker size={26} color={C.ivory} track={0.45}>no more combustion engines</Kicker>
        </Fadein>
        <Fadein t={t} at={5.4} dur={0.9} style={{position: 'absolute', left: 0, right: 0, top: 0}}>
          <Kicker size={26} color={C.goldLite} track={0.45}>everything staked on electric</Kicker>
        </Fadein>
      </div>
      <IllusTag />
    </AbsoluteFill>
  );
};

/* 21-26 : the question */
const Question: React.FC = () => {
  const t = useSec();
  const l1 = ['HOW', 'DID', 'JAGUAR'];
  const l2 = ['LOSE', 'ITS', 'WAY?'];
  const word = (w: string, i: number, base: number) => {
    const p = eo3(prog(t, base + i * 0.22, base + i * 0.22 + 0.7));
    return (
      <span key={w + i} style={{display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 40}px)`, letterSpacing: `${(1 - p) * 0.3 + 0.04}em`, marginRight: '0.3em'}}>
        {w}
      </span>
    );
  };
  const rule = eo3(prog(t, 1.8, 2.8));
  return (
    <AbsoluteFill>
      <Bg tone="red" glow={0.3} />
      <Svg style={{opacity: 0.35 - 0.2 * prog(t, 0, 4)}}>
        <g transform={`translate(${60 + t * 14} 330) scale(1.85)`}>
          <Car id="etype" uid="q" tint="#222" rim={C.silver} />
        </g>
      </Svg>
      <AbsoluteFill style={{background: 'rgba(0,0,0,0.45)'}} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 330, textAlign: 'center', fontFamily: SERIF, fontWeight: 600, fontSize: 168, color: C.ivory, lineHeight: 1.0}}>
        <div>{l1.map((w, i) => word(w, i, 0.2))}</div>
        <div>{l2.map((w, i) => word(w, i, 0.9))}</div>
      </div>
      <div style={{position: 'absolute', left: 960 - 260 * rule, width: 520 * rule, top: 780, height: 3, background: C.red}} />
    </AbsoluteFill>
  );
};

/* 25.9-28.7 : rewind to 1922 */
const Rewind: React.FC = () => {
  const t = useSec(); // 0 at 25.9
  const p = eio3(prog(t, 0.2, 2.5));
  const yr = Math.round(lerp(2026, 1922, p));
  const jit = (1 - p) * 6;
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.4} />
      <Svg>
        {Array.from({length: 80}).map((_, i) => {
          const base = 2026 - i * 4 - 0;
          const y = 540 + (base - yr) * 14;
          return <line key={i} x1={1500} x2={i % 5 === 0 ? 1580 : 1540} y1={y} y2={y} stroke={C.gold} strokeOpacity={i % 5 === 0 ? 0.8 : 0.35} strokeWidth={2} />;
        })}
        <line x1={1440} x2={1620} y1={540} y2={540} stroke={C.redLite} strokeWidth={3} />
      </Svg>
      <div style={{position: 'absolute', left: 160, top: 300, fontFamily: SERIF, fontWeight: 600, fontSize: 340, color: C.ivory, opacity: 0.95, transform: `translate(${rnd(Math.floor(t * 30)) * jit}px, 0)`}}>{yr}</div>
      <div style={{position: 'absolute', left: 170, top: 270}}>
        <Fadein t={t} at={0.1}>
          <Kicker size={22}>to understand the fall</Kicker>
        </Fadein>
      </div>
      <Flash t={t} at={2.55} dur={0.25} color="#f1e9d6" peak={0.5} />
    </AbsoluteFill>
  );
};

export const Hook: React.FC = () => (
  <>
    <Scene from={0} to={4.5} fi={0} fo={0}>
      <HeroEType />
    </Scene>
    <Scene from={4.4} to={5.5} fi={0} fo={0}>
      <Pass id="dtype" label="D-Type" sub="Le Mans winner · 1955–57" seed={1} dur={1.1} tint="#1f4b39" />
    </Scene>
    <Scene from={5.5} to={6.6} fi={0} fo={0}>
      <Pass id="etype" label="E-Type" sub="1961" seed={2} dur={1.1} dir={-1} s={2.1} />
    </Scene>
    <Scene from={6.6} to={7.7} fi={0} fo={0}>
      <Pass id="xk120" label="XK120" sub="1948" seed={4} dur={1.1} s={1.9} tint="#2a4a5a" />
    </Scene>
    <Scene from={7.6} to={8.9} fi={0} fo={0}>
      <LeMansBeat />
    </Scene>
    <Scene from={8.8} to={9.8} fi={0} fo={0}>
      <Pass id="ftype" label="F-Type" sub="2013" seed={5} dur={1} dir={-1} s={1.95} tint="#2b3a45" />
    </Scene>
    <Scene from={9.7} to={13.5} fi={0.15} fo={0.1}>
      <Elegance />
    </Scene>
    <Scene from={13.4} to={21.4} fi={0} fo={0.3}>
      <TheTurn />
    </Scene>
    <Scene from={21.0} to={26.0} fi={0.4} fo={0.2}>
      <Question />
    </Scene>
    <Scene from={25.9} to={28.8} fi={0.3} fo={0}>
      <Rewind />
    </Scene>
  </>
);
