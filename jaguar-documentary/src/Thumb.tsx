import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Car} from './kit/Car';
import {Bg, Svg, Kicker, Serif} from './kit/Stage';
import {C, SANS, SERIF} from './theme';
import {fontCss} from './kit/fonts';

export const Thumb: React.FC = () => (
  <AbsoluteFill style={{background: C.black}}>
    <style>{fontCss}</style>
    <Bg tone="char" glow={0.5} gx={65} gy={60} />
    <AbsoluteFill style={{background: 'radial-gradient(45% 35% at 70% 70%, rgba(195,161,90,0.28), rgba(0,0,0,0))'}} />
    <Svg>
      <g transform="translate(-300 520) scale(1.0)" opacity={0.9}>
        <Car id="etype" uid="th1" tint="#2c5a47" rim={C.ivory} lamp={0.8} />
      </g>
      <g transform="translate(660 600) scale(1.3)">
        <Car id="gt" uid="th2" tint="#2a2f30" rim={C.goldLite} lamp={1} />
      </g>
      <path d="M 960 140 L 960 240" stroke={C.red} strokeWidth={0} />
    </Svg>
    <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.0) 48%)'}} />
    <div style={{position: 'absolute', left: 90, top: 70}}>
      <Kicker size={30} color={C.goldLite} track={0.5}>The rise and fall of</Kicker>
      <div style={{fontFamily: SERIF, fontWeight: 700, fontSize: 300, color: C.ivory, lineHeight: 0.9, letterSpacing: '0.01em', marginTop: 6}}>JAGUAR</div>
    </div>
    <div style={{position: 'absolute', left: 90, bottom: 70}}>
      <div style={{display: 'inline-block', background: C.red, padding: '14px 32px', fontFamily: SANS, fontWeight: 700, fontSize: 56, letterSpacing: '0.14em', color: '#fff'}}>WHAT WENT WRONG?</div>
    </div>
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 10, background: C.gold}} />
  </AbsoluteFill>
);
