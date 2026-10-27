import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from '../kit/Car';
import {Bg, ChapterCard, Counter, Fadein, Flash, IllusTag, Kicker, Rise, Rule, Scene, Serif, Svg, useSec} from '../kit/Stage';
import {C, SANS, SERIF} from '../theme';
import {clamp, ease, eio3, eo3, kf, lerp, prog} from '../kit/anim';

const TYPE_TAG = 'Stylised illustration · not the production design';

/* 235.8-244.0 rebrand */
const Rebrand: React.FC = () => {
  const t = useSec(); // 0 at 235.8
  const sw = ['#e9488a', '#f28c28', '#1fb5a8', '#f2d230'];
  const old = 1 - eo3(prog(t, 2.8, 3.6));
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.35} />
      <div style={{position: 'absolute', left: 130, top: 120}}>
        <Fadein t={t} at={0.2}>
          <Kicker>2024 · the rebrand</Kicker>
        </Fadein>
      </div>
      {/* wordmarks */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 280, textAlign: 'center', height: 200}}>
        <div style={{position: 'absolute', left: 0, right: 0, fontFamily: SERIF, fontWeight: 600, fontSize: 170, letterSpacing: '0.22em', color: C.ivory, opacity: eo3(prog(t, 0.3, 1.2)) * old}}>JAGUAR</div>
        <div style={{position: 'absolute', left: 0, right: 0, fontFamily: SANS, fontWeight: 700, fontSize: 150, letterSpacing: '0.02em', color: C.ivory, opacity: 1 - old}}>JaGUar</div>
      </div>
      <Fadein t={t} at={1.5} style={{position: 'absolute', left: 0, right: 0, top: 500, textAlign: 'center', opacity: old}}>
        <Kicker size={16} color={C.ivoryDim}>Classic wordmark</Kicker>
      </Fadein>
      <Fadein t={t} at={3.4} style={{position: 'absolute', left: 0, right: 0, top: 500, textAlign: 'center', opacity: 1 - old}}>
        <Kicker size={16} color={C.ivoryDim}>New identity (stylised)</Kicker>
      </Fadein>
      {/* swatches */}
      <div style={{position: 'absolute', left: 130, top: 620, display: 'flex', gap: 0}}>
        {sw.map((c, i) => {
          const p = eo3(prog(t, 3.6 + i * 0.18, 4.4 + i * 0.18));
          return <div key={c} style={{width: 170 * p, height: 150, background: c}} />;
        })}
        <Kicker size={15} color={C.ivoryDim} style={{marginLeft: 30, alignSelf: 'flex-end', opacity: eo3(prog(t, 4.2, 4.8))}}>Bright colours</Kicker>
      </div>
      {/* ad without a car */}
      <div style={{position: 'absolute', left: 1000, top: 590, width: 790, height: 330, border: `1.5px solid ${C.silverLite}`, background: 'rgba(0,0,0,0.55)', opacity: eo3(prog(t, 5.0, 5.8)), display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
        <Serif size={74} italic>Copy nothing</Serif>
        <Kicker size={14} color={C.ivoryDim} track={0.3} style={{marginTop: 18}}>an advert without a single car</Kicker>
      </div>
      <ChapterCard n="Six" title="The Controversial Reinvention" len={3.0} />
    </AbsoluteFill>
  );
};

/* 243.9-249.6 reactions */
const Reactions: React.FC = () => {
  const t = useSec(); // 0 at 243.9
  const tilt = kf(t, [[0, 0], [1.4, -3], [3.6, -3], [4.4, 3]], eio3);
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.35} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 130, textAlign: 'center'}}>
        <Kicker>The debate</Kicker>
      </div>
      <Svg>
        <line x1={960} y1={330} x2={960} y2={860} stroke={C.silver} strokeOpacity={0.4} />
        <g transform={`rotate(${tilt} 960 400)`}>
          <line x1={360} y1={400} x2={1560} y2={400} stroke={C.goldLite} strokeWidth={3} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 200, top: 470, width: 560, textAlign: 'center', opacity: eo3(prog(t, 0.2, 0.9)), transform: `translateY(${tilt * 3}px)`}}>
        <Serif size={96}>Fearless</Serif>
        <Kicker size={14} color={C.ivoryDim} track={0.28} style={{marginTop: 12}}>“a bold reset”</Kicker>
      </div>
      <div style={{position: 'absolute', left: 1160, top: 470, width: 560, textAlign: 'center', opacity: eo3(prog(t, 2.3, 3.0)), transform: `translateY(${-tilt * 3}px)`}}>
        <Serif size={96}>A betrayal</Serif>
        <Kicker size={14} color={C.ivoryDim} track={0.28} style={{marginTop: 12}}>of Jaguar's heritage</Kicker>
      </div>
      <Fadein t={t} at={3.6} dur={0.9} style={{position: 'absolute', left: 160, right: 160, bottom: 90, textAlign: 'center'}}>
        <Kicker size={14} color={C.ivoryDim} track={0.14} style={{textTransform: 'none', letterSpacing: '0.08em'}}>Sales were already falling before the rebrand — no single decision explains the decline.</Kicker>
      </Fadein>
    </AbsoluteFill>
  );
};

/* 249.4-257.2 Type 00 vs E-Type */
const Type00: React.FC = () => {
  const t = useSec(); // 0 at 249.4
  const wipe = eio3(prog(t, 1.3, 3.1));
  return (
    <AbsoluteFill>
      <Bg tone="cold" glow={0.4} />
      <div style={{position: 'absolute', left: 130, top: 120}}>
        <Fadein t={t} at={0.2}>
          <Kicker>The radical Type 00 concept</Kicker>
        </Fadein>
        <Rule t={t} at={0.3} w={110} style={{margin: '16px 0'}} />
        <Rise t={t} at={0.4} dur={0.9}>
          <Serif size={110}>Two design languages</Serif>
        </Rise>
      </div>
      <Svg>
        <line x1={60} x2={1860} y1={862} y2={862} stroke={C.silver} strokeOpacity={0.3} />
        <g transform="translate(470 420) scale(1.0)" opacity={1 - wipe * 0.8}>
          <Car id="etype" uid="t0a" tint="#2c5a47" rim={C.ivory} ground={false} />
        </g>
        <g transform="translate(470 420) scale(1.0)" opacity={wipe}>
          <Car id="gt" uid="t0b" tint="#2a2f30" rim={C.goldLite} ground={false} lamp={wipe} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 130, bottom: 120, opacity: 1 - wipe}}>
        <Serif size={54} color={C.ivoryDim}>E-Type</Serif>
        <Kicker size={16} color={C.goldLite} track={0.3}>1961 · long bonnet, flowing curves</Kicker>
      </div>
      <div style={{position: 'absolute', left: 130, bottom: 120, opacity: wipe}}>
        <Serif size={54}>Type 00</Serif>
        <Kicker size={16} color={C.goldLite} track={0.3}>2024 · a clean-sheet idea</Kicker>
      </div>
      <IllusTag text={TYPE_TAG} />
      <Flash t={t} at={0} dur={0.3} peak={0.4} />
    </AbsoluteFill>
  );
};

/* 253.2-265.6 Type 01 reveal + specs */
const Reveal: React.FC = () => {
  const t = useSec(); // 0 at 253.2
  const s = kf(t, [[0, 0.98], [12.4, 1.12]]);
  const hp = ease(t, 7.0, 9.0, eio3) * 1000;
  return (
    <AbsoluteFill>
      <Bg tone="black" glow={0.5} gx={55} gy={55} />
      <AbsoluteFill style={{background: `radial-gradient(40% 25% at 50% 80%, rgba(195,161,90,${0.22 * eo3(prog(t, 0.4, 2))}), rgba(0,0,0,0))`}} />
      <Svg>
        <g transform={`translate(${960 - 500 * s * 1.5} ${760 - 262 * s * 1.5}) scale(${s * 1.5})`} opacity={eo3(prog(t, 0.3, 1.6))}>
          <Car id="gt" uid="rv" tint="#2a2f30" rim={C.goldLite} lamp={eo3(prog(t, 1.2, 2.2))} spin={t * 500} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 100}}>
        <Fadein t={t} at={0.5} dur={0.9}>
          <Kicker>October 2026 · unveiled</Kicker>
        </Fadein>
        <Rule t={t} at={0.7} w={110} style={{margin: '16px 0'}} />
        <Rise t={t} at={0.8} dur={1.0}>
          <Serif size={150}>Jaguar Type 01</Serif>
        </Rise>
      </div>
      <div style={{position: 'absolute', left: 130, right: 130, bottom: 110, display: 'flex', justifyContent: 'space-between'}}>
        {[
          {at: 4.6, k: 'Powertrain', v: 'Electric', s: 'four-door grand tourer'},
          {at: 7.0, k: 'Power', v: <><Counter v={hp} />+</>, s: 'horsepower'},
          {at: 9.2, k: 'Starting price', v: '£130,000', s: 'as announced'},
        ].map((c) => {
          const p = eo3(prog(t, c.at, c.at + 0.8));
          return (
            <div key={c.k} style={{width: 520, borderTop: `1.5px solid ${C.gold}`, paddingTop: 18, opacity: p, transform: `translateY(${(1 - p) * 26}px)`}}>
              <Kicker size={15} color={C.goldLite}>{c.k}</Kicker>
              <Serif size={84} style={{marginTop: 8}}>{c.v}</Serif>
              <Kicker size={14} color={C.ivoryDim} track={0.26} style={{marginTop: 6}}>{c.s}</Kicker>
            </div>
          );
        })}
      </div>
      <IllusTag text={TYPE_TAG} />
      <Flash t={t} at={0.3} dur={0.5} peak={0.7} color="#ffe9b8" />
    </AbsoluteFill>
  );
};

/* 265.4-282.6 gamble, trust, 2027 timeline */
const Gamble: React.FC = () => {
  const t = useSec(); // 0 at 265.4
  const nodes = [
    {x: 340, at: 10.9, k: 'October 2026', v: 'Unveiled'},
    {x: 960, at: 11.9, k: 'Early 2027', v: 'Orders expected'},
    {x: 1580, at: 12.9, k: 'Later in 2027', v: 'Customer deliveries'},
  ];
  const lp = eio3(prog(t, 10.6, 14.0));
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.35} />
      {/* statement phase 1: gamble / exclusivity */}
      <div style={{position: 'absolute', inset: 0, opacity: 1 - eo3(prog(t, 5.6, 6.4))}}>
        <div style={{position: 'absolute', left: 130, top: 150}}>
          <Fadein t={t} at={0.1}>
            <Kicker>A bold gamble</Kicker>
          </Fadein>
        </div>
        <div style={{position: 'absolute', left: 130, top: 260, fontFamily: SERIF, fontWeight: 600, fontSize: 130, lineHeight: 1.05}}>
          <div style={{color: C.ivoryDim, opacity: eo3(prog(t, 0.4, 1.2)), position: 'relative', display: 'inline-block'}}>
            Volume
            <div style={{position: 'absolute', left: 0, top: '56%', height: 5, width: `${100 * eo3(prog(t, 1.6, 2.4))}%`, background: C.redLite}} />
          </div>
          <div style={{color: C.ivory, opacity: eo3(prog(t, 2.8, 3.6))}}>Exclusivity</div>
        </div>
        <Fadein t={t} at={3.6} dur={0.9} style={{position: 'absolute', left: 130, top: 640}}>
          <Serif size={50} italic color={C.ivoryDim}>Aimed at exclusive luxury buyers, not the mass market</Serif>
        </Fadein>
      </div>
      <Svg>
        <g transform="translate(980 320) scale(0.9)" opacity={(1 - eo3(prog(t, 5.6, 6.4))) * eo3(prog(t, 0.3, 1.2))}>
          <Car id="gt" uid="gb" tint="#2a2f30" rim={C.goldLite} lamp={0.8} />
        </g>
      </Svg>
      {/* phase 2: trust */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 250, textAlign: 'center', opacity: eo3(prog(t, 6.2, 7.0)) * (1 - eo3(prog(t, 10.2, 10.8)))}}>
        <Serif size={84}>Power and daring design</Serif>
        <Serif size={84} italic color={C.ivoryDim} style={{marginTop: 10}}>can't automatically rebuild trust</Serif>
      </div>
      {/* phase 3: timeline */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 170, textAlign: 'center', opacity: eo3(prog(t, 10.4, 11.2))}}>
        <Kicker>The road to customers</Kicker>
      </div>
      <Svg>
        <line x1={340} y1={560} x2={lerp(340, 1580, lp)} y2={560} stroke={C.ivory} strokeOpacity={0.6} strokeWidth={2} />
        {nodes.map((n) => (
          <circle key={n.k} cx={n.x} cy={560} r={13 * eo3(prog(t, n.at, n.at + 0.5))} fill={C.char} stroke={C.goldLite} strokeWidth={3} />
        ))}
      </Svg>
      {nodes.map((n) => {
        const p = eo3(prog(t, n.at + 0.2, n.at + 0.9));
        return (
          <div key={n.k} style={{position: 'absolute', left: n.x - 260, width: 520, top: 610, textAlign: 'center', opacity: p, transform: `translateY(${(1 - p) * 18}px)`}}>
            <Kicker color={C.goldLite}>{n.k}</Kicker>
            <Serif size={56} style={{marginTop: 10}}>{n.v}</Serif>
          </div>
        );
      })}
      <div style={{position: 'absolute', left: 0, right: 0, top: 860, textAlign: 'center', opacity: eo3(prog(t, 14.2, 15.0))}}>
        <Serif size={64} italic color={C.ivoryDim}>Real success is still unproven</Serif>
      </div>
      <IllusTag text={TYPE_TAG} />
    </AbsoluteFill>
  );
};

/* 282.4-290.6 fork */
const Fork: React.FC = () => {
  const t = useSec(); // 0 at 282.4
  const up = eio3(prog(t, 0.6, 3.0));
  const down = eio3(prog(t, 3.8, 6.0));
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.45} gx={40} />
      <Svg>
        <path d="M 200 540 L 780 540" stroke={C.ivory} strokeWidth={3} fill="none" opacity={0.8} />
        <circle cx={780} cy={540} r={10} fill={C.goldLite} />
        <path d="M 780 540 C 1000 540 1100 300 1420 300" stroke={C.goldLite} strokeWidth={3} fill="none" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - up} />
        <path d="M 780 540 C 1000 540 1100 780 1420 780" stroke={C.silver} strokeOpacity={0.8} strokeWidth={3} fill="none" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - down} />
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 470, opacity: eo3(prog(t, 0.1, 0.8))}}>
        <Kicker color={C.ivoryDim}>Today</Kicker>
        <Serif size={66} style={{marginTop: 6}}>Jaguar</Serif>
      </div>
      <div style={{position: 'absolute', left: 1450, top: 210, width: 420, opacity: eo3(prog(t, 2.4, 3.2))}}>
        <Serif size={66}>The greatest comeback in British motoring?</Serif>
      </div>
      <div style={{position: 'absolute', left: 1450, top: 690, width: 420, opacity: eo3(prog(t, 5.2, 6.0))}}>
        <Serif size={66} italic color={C.ivoryDim}>Or a golden age that remains in the past?</Serif>
      </div>
    </AbsoluteFill>
  );
};

/* 290.4-299.8 heritage -> electric */
const Finale: React.FC = () => {
  const t = useSec(); // 0 at 290.4
  const w = eio3(prog(t, 2.4, 7.2));
  const s = 1.25;
  return (
    <AbsoluteFill>
      <Bg tone="warm" glow={0.5} />
      <AbsoluteFill style={{background: `radial-gradient(60% 40% at 50% 55%, rgba(195,161,90,${0.12}), rgba(0,0,0,0))`}} />
      <Svg>
        <defs>
          <clipPath id="L"><rect x={0} y={0} width={1920 * w} height={1080} /></clipPath>
          <clipPath id="R"><rect x={1920 * w} y={0} width={1920} height={1080} /></clipPath>
        </defs>
        <g clipPath="url(#R)">
          <g transform={`translate(${960 - 500 * s} ${700 - 262 * s}) scale(${s})`}>
            <Car id="etype" uid="fe" tint="#2c5a47" rim={C.ivory} lamp={0.4} />
          </g>
        </g>
        <g clipPath="url(#L)">
          <g transform={`translate(${960 - 500 * s} ${700 - 262 * s}) scale(${s})`}>
            <Car id="gt" uid="fg" tint="#2a2f30" rim={C.goldLite} lamp={1} />
          </g>
        </g>
        <line x1={1920 * w} x2={1920 * w} y1={160} y2={900} stroke={C.goldLite} strokeWidth={2} opacity={w > 0.01 && w < 0.99 ? 0.8 : 0} />
      </Svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 110, textAlign: 'center'}}>
        <Fadein t={t} at={0.2} dur={0.9}>
          <Kicker>One thing is certain</Kicker>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 140, right: 140, bottom: 90, textAlign: 'center'}}>
        <Fadein t={t} at={2.2} dur={0.9} style={{opacity: 1 - eo3(prog(t, 6.6, 7.2))}}>
          <Serif size={58} italic>The company that taught the world what a beautiful, fast car can be</Serif>
        </Fadein>
        <Fadein t={t} at={6.9} dur={0.9} style={{position: 'absolute', left: 0, right: 0, top: 0}}>
          <Serif size={62}>…must now convince it to fall in love again</Serif>
        </Fadein>
      </div>
      <IllusTag text={TYPE_TAG} />
    </AbsoluteFill>
  );
};

/* 299.4-304.5 end card */
const End: React.FC = () => {
  const t = useSec(); // 0 at 299.4
  const out = 1 - eo3(prog(t, 4.0, 5.0));
  const s = lerp(1.45, 1.6, t / 5.1);
  return (
    <AbsoluteFill style={{opacity: out}}>
      <Bg tone="black" glow={0.5} gx={60} gy={58} />
      <AbsoluteFill style={{background: 'radial-gradient(45% 28% at 62% 68%, rgba(195,161,90,0.2), rgba(0,0,0,0))'}} />
      <Svg>
        <g transform={`translate(${1180 - 500 * s} ${800 - 262 * s}) scale(${s})`}>
          <Car id="gt" uid="en" tint="#2a2f30" rim={C.goldLite} lamp={1} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 130}}>
        <Fadein t={t} at={1.2} dur={1.2}>
          <Kicker size={20}>The rise and fall of</Kicker>
        </Fadein>
        <Fadein t={t} at={1.6} dur={1.4}>
          <Serif size={130} style={{marginTop: 10}}>Jaguar</Serif>
        </Fadein>
      </div>
      <IllusTag text={TYPE_TAG} />
    </AbsoluteFill>
  );
};

export const Ch6: React.FC = () => (
  <>
    <Scene from={235.8} to={244.1} fi={0.4} fo={0.2}>
      <Rebrand />
    </Scene>
    <Scene from={243.9} to={249.6} fi={0.2} fo={0.2}>
      <Reactions />
    </Scene>
    <Scene from={249.4} to={253.4} fi={0.1} fo={0.15}>
      <Type00 />
    </Scene>
    <Scene from={253.2} to={265.6} fi={0.1} fo={0.3}>
      <Reveal />
    </Scene>
    <Scene from={265.4} to={282.6} fi={0.3} fo={0.3}>
      <Gamble />
    </Scene>
    <Scene from={282.4} to={290.6} fi={0.3} fo={0.3}>
      <Fork />
    </Scene>
    <Scene from={290.4} to={299.6} fi={0.3} fo={0.2}>
      <Finale />
    </Scene>
    <Scene from={299.4} to={304.5} fi={0.2} fo={0}>
      <End />
    </Scene>
  </>
);
