import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from '../kit/Car';
import {Gauge} from '../kit/Gauge';
import {Bg, ChapterCard, Fadein, Flash, IllusTag, Kicker, Rise, Rule, Scene, Serif, Svg, useSec} from '../kit/Stage';
import {C, SANS, SERIF} from '../theme';
import {clamp, ease, eio3, eo3, kf, lerp, prog} from '../kit/anim';

const Sweep: React.FC<{p: number}> = ({p}) => (
  <div style={{position: 'absolute', inset: 0, overflow: 'hidden', mixBlendMode: 'screen'}}>
    <div style={{position: 'absolute', top: -200, left: `${-30 + p * 150}%`, width: '12%', height: '150%', transform: 'rotate(16deg)', background: 'linear-gradient(90deg, rgba(255,236,190,0), rgba(255,236,190,0.16), rgba(255,236,190,0))'}} />
  </div>
);

/* 91.6-98.4 E-Type hero with annotations */
const Hero: React.FC = () => {
  const t = useSec(); // 0 at 91.6
  const s = kf(t, [[0, 1.55], [6.8, 1.72]]);
  const fx = kf(t, [[0, 820], [3.2, 640], [6.8, 420]], eio3);
  const cam = `translate(${960 - fx * s} ${560 - 150 * s}) scale(${s})`;
  const ann = (at: number, x1: number, x2: number, y: number, label: string, up = true) => {
    const p = eo3(prog(t, at, at + 0.8));
    return (
      <g opacity={p}>
        <line x1={x1} x2={x1 + (x2 - x1) * p} y1={y} y2={y} stroke={C.goldLite} strokeWidth={1.6} />
        <line x1={x1} x2={x1} y1={y - 8} y2={y + 8} stroke={C.goldLite} />
        <line x1={x2} x2={x2} y1={y - 8} y2={y + 8} stroke={C.goldLite} opacity={p > 0.95 ? 1 : 0} />
        <text x={(x1 + x2) / 2} y={y + (up ? -16 : 28)} textAnchor="middle" fontFamily={SANS} fontWeight={600} fontSize={13} letterSpacing={3.5} fill={C.goldLite}>{label}</text>
      </g>
    );
  };
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.5} gy={48} />
      <Svg>
        <g transform={cam}>
          <Car id="etype" uid="eh" tint="#2c5a47" rim={C.ivory} spin={t * 60} lamp={0.2} />
          {ann(3.3, 540, 940, 74, 'Long bonnet')}
          {ann(4.3, 330, 500, 6, 'Low roof')}
          {ann(5.2, 100, 330, 54, 'Sculpted curves', true)}
        </g>
      </Svg>
      <Sweep p={prog(t, 0.0, 6.8)} />
      <div style={{position: 'absolute', left: 130, top: 120}}>
        <Fadein t={t} at={0.3} dur={1.0}>
          <Kicker size={26} track={0.5}>1961</Kicker>
        </Fadein>
        <Rule t={t} at={0.6} w={120} style={{margin: '16px 0'}} />
        <Rise t={t} at={0.7} dur={1.1}>
          <Serif size={120}>Jaguar E-Type</Serif>
        </Rise>
        <Fadein t={t} at={2.3} dur={1.0}>
          <Kicker size={16} color={C.ivoryDim} track={0.3}>Geneva Motor Show · March 1961</Kicker>
        </Fadein>
      </div>
      <ChapterCard n="Three" title="The Golden Age" len={3.4} />
      <IllusTag />
      <Flash t={t} at={0.1} dur={0.5} peak={0.4} color="#ffe9b8" />
    </AbsoluteFill>
  );
};

/* 98.2-104.8 performance + price */
const Perf: React.FC = () => {
  const t = useSec(); // 0 at 98.2
  const mph = ease(t, 0.2, 2.2, eio3) * 150;
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.45} gx={25} />
      <Svg>
        <g transform="translate(-30 150) scale(1.15)" opacity={0.9}>
          <Car id="etype" uid="ep" tint="#2c5a47" rim={C.ivory} spin={t * 1500} />
        </g>
        <Gauge cx={1560} cy={330} r={190} value={mph} max={160} major={20} label="MPH" readout={`${Math.round(mph)}`} unit="E-TYPE · CLAIMED" red={150} />
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 120}}>
        <Fadein t={t} at={0.1}>
          <Kicker>Almost 150 mph</Kicker>
        </Fadein>
        <Fadein t={t} at={0.5} dur={0.9}>
          <Serif size={58} italic style={{marginTop: 14}}>3.8-litre straight-six, 265 bhp</Serif>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 130, bottom: 140}}>
        <Fadein t={t} at={3.1} dur={0.9}>
          <Kicker color={C.ivoryDim} size={20}>At a price far below its exotic rivals</Kicker>
        </Fadein>
        <Rise t={t} at={3.3} dur={1.0}>
          <Serif size={76} style={{marginTop: 10}}>Supercar performance, within reach</Serif>
        </Rise>
      </div>
      <IllusTag />
    </AbsoluteFill>
  );
};

/* 104.6-115 cultural phenomenon + formula */
const Phenom: React.FC = () => {
  const t = useSec(); // 0 at 104.6
  const tints = ['#2c5a47', '#7a1e22', '#2c4a6a', '#8a8f93', '#b9a46a'];
  const cards = [
    {at: 5.2, a: 'Race-car', b: 'excitement'},
    {at: 6.4, a: 'Genuine', b: 'luxury'},
    {at: 7.7, a: 'An attainable', b: 'price'},
  ];
  const phase2 = eo3(prog(t, 3.6, 4.6));
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.5} />
      <Svg>
        <g opacity={1 - phase2}>
          {tints.map((tn, i) => {
            const p = eo3(prog(t, 0.1 + i * 0.28, 0.9 + i * 0.28));
            return (
              <g key={i} transform={`translate(${60 + (i % 2) * 520 + (i === 4 ? 260 : 0)} ${130 + Math.floor(i / 2) * 270 + (i === 4 ? 0 : 0)}) scale(0.5)`} opacity={p}>
                <Car id="etype" uid={'ph' + i} tint={tn} rim={C.ivory} spin={0} />
              </g>
            );
          })}
          <g transform="translate(1200 150) scale(0.5)" opacity={eo3(prog(t, 1.4, 2.2))}>
            <Car id="etype" uid="ph9" tint="#1a1a1a" rim={C.ivory} />
          </g>
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 760, textAlign: 'center', opacity: 1 - phase2}}>
        <Rise t={t} at={0.4} dur={1.0}>
          <Serif size={108}>A cultural phenomenon</Serif>
        </Rise>
      </div>
      {/* formula */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 150, textAlign: 'center', opacity: phase2}}>
        <Kicker>The impossible formula</Kicker>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 330, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 30, opacity: phase2}}>
        {cards.map((c, i) => {
          const p = eo3(prog(t, c.at, c.at + 0.7));
          return (
            <React.Fragment key={c.b}>
              <div style={{width: 400, height: 250, border: `1.5px solid ${C.gold}`, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', opacity: p, transform: `translateY(${(1 - p) * 30}px)`, background: 'rgba(0,0,0,0.25)'}}>
                <Serif size={56} italic color={C.ivoryDim}>{c.a}</Serif>
                <Serif size={78}>{c.b}</Serif>
              </div>
              {i < 2 && <div style={{fontFamily: SERIF, fontSize: 80, color: C.gold, opacity: p}}>+</div>}
            </React.Fragment>
          );
        })}
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 700, textAlign: 'center', opacity: eo3(prog(t, 9.0, 9.9))}}>
        <Kicker size={22} color={C.ivoryDim}>=</Kicker>
        <Serif size={120} style={{marginTop: 10}}>E-Type</Serif>
      </div>
      <IllusTag />
    </AbsoluteFill>
  );
};

/* 115-124.8 XJ + stability */
const XJ: React.FC = () => {
  const t = useSec(); // 0 at 115.0
  const gray = eo3(prog(t, 7.0, 8.4));
  const words = [['Grace', 4.9], ['Space', 5.5], ['Pace', 6.2]] as const;
  const crack = eio3(prog(t, 7.2, 9.0));
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', inset: 0, filter: `grayscale(${gray}) brightness(${1 - gray * 0.25})`}}>
        <Bg tone="warm" glow={0.45} gx={60} />
        <Svg>
          <g transform="translate(150 360) scale(1.5)">
            <Car id="saloon" uid="xj" tint="#2c4a6a" rim={C.ivory} spin={t * 400} />
          </g>
        </Svg>
        <div style={{position: 'absolute', left: 130, top: 120}}>
          <Fadein t={t} at={0.2}>
            <Kicker>Saloon elegance</Kicker>
          </Fadein>
          <Rule t={t} at={0.3} w={110} style={{margin: '16px 0'}} />
          <Rise t={t} at={0.4} dur={0.9}>
            <Serif size={120}>XJ · 1968</Serif>
          </Rise>
        </div>
        <div style={{position: 'absolute', left: 130, bottom: 120, display: 'flex', gap: 60, fontFamily: SERIF, fontStyle: 'italic', fontWeight: 500, fontSize: 96, color: C.ivory}}>
          {words.map(([w, at]) => (
            <span key={w} style={{opacity: eo3(prog(t, at, at + 0.5)), transform: `translateY(${(1 - eo3(prog(t, at, at + 0.5))) * 26}px)`}}>
              {w}
            </span>
          ))}
        </div>
      </div>
      <Svg>
        <path d="M 1180,0 L 1130,210 L 1210,330 L 1100,520 L 1170,640 L 1060,860 L 1110,1080" fill="none" stroke={C.red} strokeWidth={3} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - crack} opacity={0.85} />
      </Svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 480, textAlign: 'center', opacity: eo3(prog(t, 7.6, 8.4))}}>
        <Serif size={66} italic color={C.ivory} style={{textShadow: '0 4px 30px #000'}}>Success didn't guarantee stability</Serif>
      </div>
      <IllusTag />
    </AbsoluteFill>
  );
};

export const Ch3: React.FC = () => (
  <>
    <Scene from={91.6} to={98.4} fi={0.3} fo={0.2}>
      <Hero />
    </Scene>
    <Scene from={98.2} to={104.8} fi={0.2} fo={0.2}>
      <Perf />
    </Scene>
    <Scene from={104.6} to={115.2} fi={0.2} fo={0.2}>
      <Phenom />
    </Scene>
    <Scene from={115.0} to={125.2} fi={0.2} fo={0.3}>
      <XJ />
    </Scene>
  </>
);
