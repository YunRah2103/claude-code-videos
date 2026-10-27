import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from '../kit/Car';
import {Gauge} from '../kit/Gauge';
import {Bg, ChapterCard, Counter, Fadein, Flash, IllusTag, Kicker, Rise, Rule, Scene, Serif, Svg, useSec} from '../kit/Stage';
import {C, SANS, SERIF} from '../theme';
import {clamp, ease, eio3, eo3, kf, lerp, prog} from '../kit/anim';

const Arrow: React.FC<{up: boolean; color: string; p: number}> = ({up, color, p}) => (
  <svg width={70} height={90} viewBox="0 0 70 90" style={{opacity: p, transform: `translateY(${(1 - p) * (up ? 20 : -20)}px)`}}>
    <path d={up ? 'M 35 6 L 62 44 L 44 44 L 44 84 L 26 84 L 26 44 L 8 44 Z' : 'M 35 84 L 62 46 L 44 46 L 44 6 L 26 6 L 26 46 L 8 46 Z'} fill={color} />
  </svg>
);

/* 190.4-199.0 scale + JLR siblings */
const Scale: React.FC = () => {
  const t = useSec(); // 0 at 190.4
  const tiles = [
    {n: 'Jaguar', up: false, at: 3.6, col: C.redLite},
    {n: 'Range Rover', up: true, at: 4.9, col: C.goldLite},
    {n: 'Defender', up: true, at: 5.6, col: C.goldLite},
  ];
  return (
    <AbsoluteFill>
      <Bg tone="red" glow={0.3} />
      <div style={{position: 'absolute', left: 130, top: 120}}>
        <Fadein t={t} at={0.2}>
          <Kicker>Scale matters</Kicker>
        </Fadein>
        <Rise t={t} at={0.3} dur={1.0}>
          <Serif size={96} style={{marginTop: 14}}>Jaguar couldn't match German scale</Serif>
        </Rise>
      </div>
      <div style={{position: 'absolute', left: 130, top: 480}}>
        <Fadein t={t} at={2.9} dur={0.8}>
          <Kicker color={C.ivoryDim}>Even inside Jaguar Land Rover</Kicker>
        </Fadein>
        <div style={{display: 'flex', gap: 40, marginTop: 34}}>
          {tiles.map((x) => {
            const p = eo3(prog(t, x.at, x.at + 0.7));
            return (
              <div key={x.n} style={{width: 520, height: 270, border: `1.5px solid ${x.col}`, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 46px', opacity: p, transform: `translateY(${(1 - p) * 30}px)`}}>
                <div>
                  <Serif size={62}>{x.n}</Serif>
                  <Kicker size={15} color={x.col} track={0.3} style={{marginTop: 12}}>{x.up ? 'Stronger seller' : 'Falling behind'}</Kicker>
                </div>
                <Arrow up={x.up} color={x.col} p={p} />
              </div>
            );
          })}
        </div>
      </div>
      <ChapterCard n="Five" title="The Fall" len={3.0} />
    </AbsoluteFill>
  );
};

/* 198.4-211.8 sales chart */
const Chart: React.FC = () => {
  const t = useSec(); // 0 at 198.4
  const X0 = 260, W = 1400, Y0 = 800, K = 2.5; // px per 1k
  const fy = ['FY2018/19', 'FY2019/20', 'FY2020/21', 'FY2021/22', 'FY2022/23', 'FY2023/24'];
  const cw = W / 6;
  const bx = (i: number) => X0 + cw * i + cw / 2;
  const axis = eio3(prog(t, 0.2, 2.0));
  const h1 = ease(t, 2.1, 4.4, eo3) * 180 * K;
  const h2 = ease(t, 10.0, 12.2, eo3) * 67 * K;
  const s = kf(t, [[0, 1.0], [7, 1.0], [13.4, 1.17]], eio3);
  const fx = kf(t, [[0, 960], [7, 960], [13.4, 1330]], eio3);
  const slope = eio3(prog(t, 8.0, 11.2));
  const cnt1 = ease(t, 2.1, 4.4, eo3) * 180000;
  const cnt2 = ease(t, 10.0, 12.2, eo3) * 67000;
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.3} gx={55} />
      <div style={{position: 'absolute', left: 130, top: 90}}>
        <Fadein t={t} at={0.3}>
          <Kicker>Jaguar global retail sales</Kicker>
        </Fadein>
        <Serif size={60} italic style={{marginTop: 10, opacity: 0.95}}>Jaguar brand only · financial years</Serif>
      </div>
      <AbsoluteFill style={{transform: `scale(${s})`, transformOrigin: `${fx}px 600px`}}>
        <Svg>
          {[0, 50, 100, 150, 200].map((v) => (
            <g key={v} opacity={axis}>
              <line x1={X0} x2={X0 + W * axis} y1={Y0 - v * K} y2={Y0 - v * K} stroke={C.silver} strokeOpacity={v === 0 ? 0.7 : 0.14} />
              <text x={X0 - 22} y={Y0 - v * K + 6} textAnchor="end" fontFamily={SANS} fontWeight={500} fontSize={17} fill={C.ivoryDim}>{v === 0 ? '0' : `${v}k`}</text>
            </g>
          ))}
          {fy.map((l, i) => (
            <text key={l} x={bx(i)} y={Y0 + 44} textAnchor="middle" fontFamily={SANS} fontWeight={600} fontSize={18} letterSpacing={2} fill={i === 0 || i === 5 ? C.ivory : C.ivoryDim} opacity={axis * (i === 0 || i === 5 ? 1 : 0.55)}>{l}</text>
          ))}
          {/* bar 1 */}
          <rect x={bx(0) - 70} y={Y0 - h1} width={140} height={h1} fill={C.silver} fillOpacity={0.85} />
          <rect x={bx(0) - 70} y={Y0 - h1} width={140} height={3} fill={C.ivory} />
          {/* bar 2 */}
          <rect x={bx(5) - 70} y={Y0 - h2} width={140} height={h2} fill={C.red} fillOpacity={0.9} />
          <rect x={bx(5) - 70} y={Y0 - h2} width={140} height={3} fill={C.redLite} />
          {/* slope */}
          <line x1={bx(0) + 80} y1={Y0 - 180 * K} x2={lerp(bx(0) + 80, bx(5) - 80, slope)} y2={lerp(Y0 - 180 * K, Y0 - 67 * K - 6, slope)} stroke={C.redLite} strokeWidth={3} strokeDasharray="12 10" opacity={slope > 0 ? 1 : 0} />
          {slope > 0.98 && <path d={`M ${bx(5) - 80} ${Y0 - 67 * K - 6} l -26 -4 l 8 -16 z`} fill={C.redLite} transform="rotate(0)" />}
        </Svg>
        <div style={{position: 'absolute', left: bx(0) - 150, width: 300, textAlign: 'center', top: Y0 - h1 - 78, opacity: eo3(prog(t, 4.2, 4.9))}}>
          <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 56, color: C.ivory}}>180,000+</div>
        </div>
        <div style={{position: 'absolute', left: bx(5) - 170, width: 340, textAlign: 'center', top: Y0 - h2 - 78, opacity: eo3(prog(t, 12.0, 12.7))}}>
          <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 56, color: C.redLite}}>under 67,000</div>
        </div>
      </AbsoluteFill>
      <div style={{position: 'absolute', left: 740, top: 360, opacity: eo3(prog(t, 11.0, 11.8))}}>
        <Serif size={64} italic color={C.redLite}>down by more than 60%</Serif>
      </div>
      <Fadein t={t} at={1.5} style={{position: 'absolute', left: 130, bottom: 58}}>
        <Kicker size={13} color="rgba(241,233,214,0.45)" track={0.18} style={{textTransform: 'none', letterSpacing: '0.06em'}}>Figures as stated in the narration: more than 180,000 in FY2018/19; under 67,000 in FY2023/24. Intermediate years not plotted. Financial years end 31 March.</Kicker>
      </Fadein>
    </AbsoluteFill>
  );
};

/* 211.6-221.6 start again, 2024 models end */
const StartAgain: React.FC = () => {
  const t = useSec(); // 0 at 211.6
  const models = [
    {n: 'XE', id: 'saloon', at: 7.8, tint: '#2c4a6a'},
    {n: 'XF', id: 'saloon', at: 8.6, tint: '#5a2a2c'},
    {n: 'E-Pace', id: 'suv', at: 9.4, tint: '#2a3a42'},
    {n: 'F-Type', id: 'ftype', at: 10.1, tint: '#7a1e22'},
  ];
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.3} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 110, textAlign: 'center'}}>
        <Rise t={t} at={0.1} dur={1.0}>
          <Serif size={84}>A staggering decision</Serif>
        </Rise>
        <Fadein t={t} at={4.4} dur={0.9}>
          <Serif size={58} italic color={C.ivoryDim} style={{marginTop: 12}}>Start again.</Serif>
        </Fadein>
      </div>
      <Svg>
        {models.map((m, i) => {
          const p = eo3(prog(t, 5.8 + i * 0.2, 6.6 + i * 0.2));
          const out = eo3(prog(t, m.at, m.at + 1.0));
          return (
            <g key={m.n} transform={`translate(${60 + (i % 2) * 940} ${330 + Math.floor(i / 2) * 330}) scale(0.82)`} opacity={p}>
              <g style={{filter: `grayscale(${out}) brightness(${1 - out * 0.55})`}}>
                <Car id={m.id} uid={'sa' + i} tint={m.tint} rim={C.silverLite} />
              </g>
            </g>
          );
        })}
      </Svg>
      {models.map((m, i) => {
        const out = eo3(prog(t, m.at, m.at + 1.0));
        return (
          <div key={m.n} style={{position: 'absolute', left: 130 + (i % 2) * 940, top: 540 + Math.floor(i / 2) * 330, display: 'flex', gap: 22, alignItems: 'baseline', opacity: eo3(prog(t, 6.4, 7))}}>
            <Serif size={46} color={out > 0.5 ? C.ivoryDim : C.ivory}>{m.n}</Serif>
            <Kicker size={14} color={C.redLite} track={0.3} style={{opacity: out}}>production ends</Kicker>
          </div>
        );
      })}
      <Fadein t={t} at={6.2} dur={0.7} style={{position: 'absolute', left: 0, right: 0, top: 300, textAlign: 'center'}}>
        <Kicker color={C.ivoryDim}>2024 · familiar models discontinued</Kicker>
      </Fadein>
      <IllusTag />
    </AbsoluteFill>
  );
};

/* 221.4-229.2 last combustion car */
const Last: React.FC = () => {
  const t = useSec(); // 0 at 221.4
  const rpm = kf(t, [[0, 0.8], [1.2, 0.8], [1.6, 3.2], [2.4, 1.8], [3.6, 2.6], [5.0, 1.5], [6.0, 0.9], [6.6, 0.33], [6.8, 0]], eio3);
  const lamp = clamp(1 - prog(t, 6.2, 6.8));
  const dark = prog(t, 6.6, 7.6);
  return (
    <AbsoluteFill>
      <Bg tone="black" glow={0.2} gx={50} gy={55} />
      <Svg>
        <g transform="translate(110 360) scale(1.1)" opacity={1 - dark * 0.85}>
          <Car id="suv" uid="last" tint="#26302d" rim={C.silverLite} lamp={lamp} spin={t * 60 * (1 - prog(t, 5, 6.6))} />
        </g>
        <g opacity={1 - dark}>
          <Gauge cx={1560} cy={300} r={150} value={rpm} max={8} major={1} label="RPM x1000" red={6.5} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 130, top: 120, opacity: 1 - dark * 0.7}}>
        <Fadein t={t} at={0.1} dur={0.9}>
          <Kicker color={C.redLite}>December 2025</Kicker>
        </Fadein>
        <Rise t={t} at={0.3} dur={1.0}>
          <Serif size={92} style={{marginTop: 12}}>The last combustion-engine Jaguar</Serif>
        </Rise>
        <Fadein t={t} at={3.0} dur={1.0}>
          <Serif size={50} italic color={C.ivoryDim} style={{marginTop: 14}}>leaves the production line</Serif>
        </Fadein>
      </div>
      <IllusTag />
    </AbsoluteFill>
  );
};

/* 229-236 empty podium */
const Empty: React.FC = () => {
  const t = useSec(); // 0 at 229.0
  const on = eo3(prog(t, 0.6, 2.4));
  return (
    <AbsoluteFill>
      <Bg tone="black" glow={0.1} />
      <Svg>
        <defs>
          <linearGradient id="cone" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff3d6" stopOpacity="0.28" />
            <stop offset="1" stopColor="#fff3d6" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <path d="M 900 0 L 1020 0 L 1300 830 L 620 830 Z" fill="url(#cone)" opacity={on} />
        <ellipse cx={960} cy={832} rx={340} ry={42} fill="#15191a" stroke={C.silverLite} strokeOpacity={0.5} />
        <ellipse cx={960} cy={822} rx={330} ry={36} fill="#242a2b" opacity={on} />
        <rect x={620} y={832} width={680} height={50} fill="#0c0e0e" />
      </Svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 160, textAlign: 'center'}}>
        <Fadein t={t} at={1.8} dur={1.2}>
          <Serif size={84}>No new cars at all</Serif>
        </Fadein>
        <Fadein t={t} at={4.2} dur={1.0}>
          <Kicker size={20} color={C.ivoryDim} style={{marginTop: 22}}>the brand that defined the British sports car · temporarily</Kicker>
        </Fadein>
      </div>
    </AbsoluteFill>
  );
};

export const Ch5: React.FC = () => (
  <>
    <Scene from={190.4} to={198.8} fi={0.25} fo={0.2}>
      <Scale />
    </Scene>
    <Scene from={198.4} to={211.8} fi={0.2} fo={0.25}>
      <Chart />
    </Scene>
    <Scene from={211.6} to={221.8} fi={0.25} fo={0.2}>
      <StartAgain />
    </Scene>
    <Scene from={221.4} to={229.4} fi={0.2} fo={0.6}>
      <Last />
    </Scene>
    <Scene from={229.0} to={236.2} fi={0.8} fo={0.3}>
      <Empty />
    </Scene>
  </>
);
