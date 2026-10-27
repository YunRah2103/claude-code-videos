import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from '../kit/Car';
import {Chain} from '../kit/Chain';
import {Bg, ChapterCard, Fadein, Flash, IllusTag, Kicker, Rise, Rule, Scene, Serif, Svg, useSec} from '../kit/Stage';
import {C, SANS, SERIF} from '../theme';
import {clamp, ease, eio3, eo3, kf, lerp, prog, rnd} from '../kit/anim';

const Tag: React.FC<{t: number; at: number; children: React.ReactNode; x: number; y: number}> = ({t, at, children, x, y}) => {
  const p = eo3(prog(t, at, at + 0.35));
  return (
    <div style={{position: 'absolute', left: x, top: y, opacity: p, transform: `scale(${1.15 - 0.15 * p})`, transformOrigin: 'left center', border: `1.5px solid ${C.redLite}`, padding: '10px 22px', fontFamily: SANS, fontWeight: 700, fontSize: 21, letterSpacing: '0.28em', color: C.redLite, textTransform: 'uppercase', background: 'rgba(40,6,8,0.45)'}}>
      {children}
    </div>
  );
};

/* 125.2-136.2 British Leyland */
const Leyland: React.FC = () => {
  const t = useSec(); // 0 at 125.2
  const shake = prog(t, 5.5, 9.5) * 2;
  return (
    <AbsoluteFill>
      <Bg tone="cold" glow={0.3} gx={30} />
      <div style={{position: 'absolute', inset: 0, transform: `translate(${(rnd(Math.floor(t * 24)) - 0.5) * shake}px, ${(rnd(Math.floor(t * 24) + 9) - 0.5) * shake}px)`}}>
        <div style={{position: 'absolute', left: 130, top: 110}}>
          <Fadein t={t} at={0.3}>
            <Kicker color={C.ivoryDim}>The late 1960s</Kicker>
          </Fadein>
        </div>
        <Chain t={t} x={300} y={330} w={500} h={200} gap={260} links={[{name: 'Jaguar', year: 'Independent', at: 0.6}, {name: 'British Leyland', year: '1968 · giant group', at: 2.6, tone: 'ivory'}]} />
        <Tag t={t} at={5.7} x={1040} y={620}>Industrial turmoil</Tag>
        <Tag t={t} at={7.2} x={1040} y={700}>Financial problems</Tag>
        <Tag t={t} at={8.4} x={1040} y={780}>Quality concerns</Tag>
        <Fadein t={t} at={9.3} dur={0.8} style={{position: 'absolute', left: 300, top: 640}}>
          <Serif size={64} italic>…and confidence shook</Serif>
        </Fadein>
      </div>
      <ChapterCard n="Four" title="The Beginning of the Decline" len={3.2} />
    </AbsoluteFill>
  );
};

/* 136.2-141.6 badge survived */
const Vulnerable: React.FC = () => {
  const t = useSec(); // 0 at 136.2
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.3} />
      <Svg style={{opacity: 0.5}}>
        <g transform="translate(300 330) scale(1.4)">
          <Car id="saloon" uid="vul" tint="#2a3230" rim={C.silver} fill={0.8} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 200, textAlign: 'center'}}>
        <Rise t={t} at={0.1} dur={1.0}>
          <Serif size={96}>The badge survived</Serif>
        </Rise>
        <Fadein t={t} at={1.5} dur={0.9}>
          <Serif size={66} italic color={C.ivoryDim} style={{marginTop: 14}}>but the business was vulnerable</Serif>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 150, textAlign: 'center', opacity: eo3(prog(t, 3.3, 4.0))}}>
        <Kicker size={22}>Flashes of brilliance</Kicker>
      </div>
      <Flash t={t} at={3.3} dur={0.5} peak={0.3} color="#ffe9b8" />
    </AbsoluteFill>
  );
};

/* 141.6-150.4 independence + Le Mans */
const Independence: React.FC = () => {
  const t = useSec(); // 0 at 141.6
  const plaques = [
    {y: 1988, c: 'XJR-9', at: 5.6},
    {y: 1990, c: 'XJR-12', at: 7.4},
  ];
  return (
    <AbsoluteFill>
      <Bg tone="green" glow={0.4} gx={70} />
      <div style={{position: 'absolute', left: 130, top: 130}}>
        <Fadein t={t} at={0.2}>
          <Kicker>Independence regained</Kicker>
        </Fadein>
        <Rise t={t} at={0.4} dur={1.0}>
          <Serif size={230} style={{marginTop: 10}}>1984</Serif>
        </Rise>
        <Fadein t={t} at={1.6} dur={0.9}>
          <Kicker size={18} color={C.ivoryDim} track={0.28}>Floated on the London Stock Exchange</Kicker>
        </Fadein>
      </div>
      <Svg>
        <g transform="translate(900 280) scale(1.0)" opacity={eo3(prog(t, 3.0, 4.2))}>
          <Car id="groupc" uid="gc" tint="#1f4b39" rim={C.silverLite} spin={t * 900} />
        </g>
      </Svg>
      <div style={{position: 'absolute', left: 130, bottom: 120, display: 'flex', gap: 40}}>
        {plaques.map((p) => {
          const a = eo3(prog(t, p.at, p.at + 0.6));
          return (
            <div key={p.y} style={{border: `1.5px solid ${C.gold}`, padding: '16px 36px', opacity: a, transform: `translateY(${(1 - a) * 24}px)`}}>
              <Kicker size={14} color={C.ivoryDim}>Le Mans winner</Kicker>
              <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 70, color: C.goldLite, lineHeight: 1.1}}>{p.y}</div>
              <Kicker size={16} color={C.ivory} track={0.3}>Jaguar {p.c}</Kicker>
            </div>
          );
        })}
      </div>
      <IllusTag />
      <Flash t={t} at={5.6} dur={0.25} peak={0.3} />
      <Flash t={t} at={7.4} dur={0.25} peak={0.3} />
    </AbsoluteFill>
  );
};

/* 150.2-161 German rivals */
const Germans: React.FC = () => {
  const t = useSec(); // 0 at 150.2
  const rivals = [
    {n: 'BMW', at: 2.5},
    {n: 'Mercedes-Benz', at: 3.5},
    {n: 'Audi', at: 4.7},
  ];
  const types = ['saloon', 'ftype', 'suv', 'ipace', 'saloon', 'suv', 'ftype', 'saloon', 'ipace', 'suv', 'saloon', 'ftype'];
  const rows = ['Technology', 'Quality', 'Model range'];
  return (
    <AbsoluteFill>
      <Bg tone="cold" glow={0.35} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 100, textAlign: 'center'}}>
        <Fadein t={t} at={0.1}>
          <Kicker>The world was changing</Kicker>
        </Fadein>
      </div>
      <div style={{position: 'absolute', left: 120, right: 120, top: 220, display: 'flex', gap: 36}}>
        {rivals.map((r, ri) => {
          const p = eo3(prog(t, r.at, r.at + 0.8));
          return (
            <div key={r.n} style={{flex: 1, height: 640, border: '1px solid rgba(241,233,214,0.25)', background: 'rgba(0,0,0,0.3)', opacity: p, transform: `translateY(${(1 - p) * 40}px)`, padding: '36px 34px', position: 'relative'}}>
              <Serif size={58}>{r.n}</Serif>
              <Rule t={t} at={r.at + 0.3} w={90} style={{margin: '16px 0 26px'}} />
              {rows.map((row, i) => {
                const rp = eo3(prog(t, 5.4 + i * 0.9 + ri * 0.15, 6.0 + i * 0.9 + ri * 0.15));
                return (
                  <div key={row} style={{display: 'flex', alignItems: 'center', gap: 14, marginBottom: 18, opacity: rp}}>
                    <svg width={26} height={26} viewBox="0 0 26 26"><path d="M 4 14 L 10 20 L 22 6" stroke={C.goldLite} strokeWidth={3} fill="none" /></svg>
                    <Kicker size={17} color={C.ivory} track={0.22}>{`Invested in ${row.toLowerCase()}`}</Kicker>
                  </div>
                );
              })}
              <svg width={490} height={330} viewBox="0 0 1500 1010" style={{position: 'absolute', left: 22, bottom: 14}}>
                {types.map((tp, i) => {
                  const cp = eo3(prog(t, 7.0 + i * 0.22 + ri * 0.08, 7.5 + i * 0.22 + ri * 0.08));
                  return (
                    <g key={i} transform={`translate(${(i % 3) * 500} ${Math.floor(i / 3) * 250}) scale(0.5)`} opacity={cp}>
                      <Car id={tp} uid={`gm${ri}${i}`} tint="#2a3a42" rim={C.silver} ground={false} />
                    </g>
                  );
                })}
              </svg>
            </div>
          );
        })}
      </div>
      <Fadein t={t} at={8.2} dur={0.8} style={{position: 'absolute', left: 0, right: 0, bottom: 70, textAlign: 'center'}}>
        <Serif size={44} italic color={C.ivoryDim}>…and ever-expanding model ranges</Serif>
      </Fadein>
    </AbsoluteFill>
  );
};

/* 160.6-175.6 Ford + volume + Tata */
const Owners: React.FC = () => {
  const t = useSec(); // 0 at 160.6
  const links = [
    {name: 'Jaguar', year: '1984 · independent', at: 0.2, tone: 'ivory' as const},
    {name: 'Ford', year: '1989 · acquires Jaguar', note: 'about $2.5 billion', at: 0.6, tone: 'gold' as const},
    {name: 'Tata Motors', year: '2008 · buys JLR', note: 'about $2.3 billion', at: 11.4, tone: 'gold' as const},
  ];
  const showTata = prog(t, 11.0, 11.4);
  const ident = eo3(prog(t, 7.6, 9.0));
  return (
    <AbsoluteFill>
      <Bg tone="char" glow={0.35} />
      <Chain t={t} x={180} y={150} w={440} h={190} gap={150} links={links.slice(0, showTata > 0 ? 3 : 2)} />
      <Svg>
        {/* S-Type and X-Type */}
        <g opacity={eo3(prog(t, 4.2, 5.0)) * (1 - ident * 0.6)}>
          <g transform="translate(100 400) scale(0.85)"><Car id="saloon" uid="st" tint="#2a4a5a" rim={C.silverLite} /></g>
          <g transform="translate(1000 400) scale(0.85)" opacity={eo3(prog(t, 5.2, 6.0))}><Car id="saloon" uid="xt" tint="#5a2a2c" rim={C.silverLite} /></g>
        </g>
        {ident > 0 && (
          <g opacity={ident * (1 - prog(t, 10.2, 10.8))}>
            {[0, 1, 2, 3].map((i) => (
              <g key={i} transform={`translate(${460 + i * 9} ${400 + i * 5}) scale(0.85)`} opacity={0.25}>
                <Car id={['saloon', 'saloon', 'ftype', 'saloon'][i]} uid={'id' + i} tint="#222" rim={C.silver} ground={false} />
              </g>
            ))}
          </g>
        )}
      </Svg>
      <div style={{position: 'absolute', left: 180, top: 665, opacity: eo3(prog(t, 4.4, 5.0)) * (1 - ident)}}>
        <Kicker size={18}>S-Type · 1999</Kicker>
      </div>
      <div style={{position: 'absolute', left: 1080, top: 665, opacity: eo3(prog(t, 5.4, 6.0)) * (1 - ident)}}>
        <Kicker size={18}>X-Type · 2001</Kicker>
      </div>
      <div style={{position: 'absolute', left: 180, top: 780, opacity: eo3(prog(t, 2.2, 3.0)) * (1 - ident), width: 1200}}>
        <Serif size={60} italic>Ford pushed for growth — new buyers, new models</Serif>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 760, textAlign: 'center', opacity: ident * (1 - prog(t, 10.2, 10.8))}}>
        <Serif size={86}>What, exactly, is a Jaguar?</Serif>
        <Kicker size={18} color={C.ivoryDim} style={{marginTop: 20}}>Chasing volume made the identity harder to define</Kicker>
      </div>
      <IllusTag />
      <Flash t={t} at={0.6} dur={0.3} peak={0.25} />
      <Flash t={t} at={11.6} dur={0.3} peak={0.25} />
    </AbsoluteFill>
  );
};

/* 175.4-190.4 fightback */
const Fightback: React.FC = () => {
  const t = useSec(); // 0 at 175.4
  const cars = [
    {id: 'saloon', n: 'XF', y: '2008', at: 1.5, tint: '#2c4a6a'},
    {id: 'ftype', n: 'F-Type', y: '2013', at: 3.0, tint: '#7a1e22'},
    {id: 'suv', n: 'F-Pace', y: '2016', at: 4.4, tint: '#2a3a42'},
    {id: 'ipace', n: 'I-Pace', y: '2018 · all-electric', at: 5.5, tint: '#2c5a47'},
  ];
  const dim = eo3(prog(t, 12.0, 13.2));
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', inset: 0, filter: `grayscale(${dim}) brightness(${1 - dim * 0.35})`}}>
        <Bg tone="char" glow={0.4} gx={50} />
        <div style={{position: 'absolute', left: 0, right: 0, top: 110, textAlign: 'center'}}>
          <Fadein t={t} at={0.1}>
            <Kicker>2008 onwards · the fightback</Kicker>
          </Fadein>
        </div>
        <Svg>
          {cars.map((c, i) => {
            const p = eo3(prog(t, c.at, c.at + 0.9));
            const col = i % 2, row = Math.floor(i / 2);
            return (
              <g key={c.n} transform={`translate(${70 + col * 920} ${230 + row * 380}) scale(0.88)`} opacity={p}>
                <Car id={c.id} uid={'fb' + i} tint={c.tint} rim={C.silverLite} spin={t * 200} draw={eo3(prog(t, c.at, c.at + 1.2))} />
              </g>
            );
          })}
        </Svg>
        {cars.map((c, i) => {
          const p = eo3(prog(t, c.at + 0.5, c.at + 1.2));
          const col = i % 2, row = Math.floor(i / 2);
          return (
            <div key={c.n} style={{position: 'absolute', left: 130 + col * 920, top: 500 + row * 380, opacity: p}}>
              <Serif size={54}>{c.n}</Serif>
              <Kicker size={14} color={C.goldLite} track={0.3}>{c.y}</Kicker>
            </div>
          );
        })}
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 70, textAlign: 'center'}}>
        <Fadein t={t} at={10.7} dur={0.9} style={{opacity: 1 - eo3(prog(t, 12, 12.4))}}>
          <Serif size={50} italic>Some were excellent</Serif>
        </Fadein>
        <Fadein t={t} at={12.3} dur={0.9} style={{position: 'absolute', left: 0, right: 0, top: 0}}>
          <Serif size={62} italic>But being good wasn't enough</Serif>
        </Fadein>
      </div>
      <IllusTag />
    </AbsoluteFill>
  );
};

export const Ch4: React.FC = () => (
  <>
    <Scene from={125.2} to={136.4} fi={0.2} fo={0.25}>
      <Leyland />
    </Scene>
    <Scene from={136.2} to={141.8} fi={0.25} fo={0.2}>
      <Vulnerable />
    </Scene>
    <Scene from={141.6} to={150.4} fi={0.2} fo={0.25}>
      <Independence />
    </Scene>
    <Scene from={150.2} to={160.8} fi={0.25} fo={0.2}>
      <Germans />
    </Scene>
    <Scene from={160.6} to={175.6} fi={0.2} fo={0.25}>
      <Owners />
    </Scene>
    <Scene from={175.4} to={190.6} fi={0.25} fo={0.3}>
      <Fightback />
    </Scene>
  </>
);
