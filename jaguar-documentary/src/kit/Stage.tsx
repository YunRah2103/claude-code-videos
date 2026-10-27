import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, staticFile} from 'remotion';
import {C, SANS, SERIF} from '../theme';
import {clamp, eo3, prog, rnd} from './anim';

export const useSec = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return f / fps;
};

/** Absolute-time scene. Children get local time through useSec(). fade = seconds of cross-dissolve at each edge. */
export const Scene: React.FC<{from: number; to: number; fi?: number; fo?: number; children: React.ReactNode}> = ({from, to, fi = 0.25, fo = 0.25, children}) => {
  const fps = 30;
  const start = Math.round(from * fps);
  const len = Math.max(1, Math.round((to - from) * fps));
  return (
    <Sequence from={start} durationInFrames={len} layout="none">
      <Fade len={len / fps} fi={fi} fo={fo}>
        {children}
      </Fade>
    </Sequence>
  );
};
const Fade: React.FC<{len: number; fi: number; fo: number; children: React.ReactNode}> = ({len, fi, fo, children}) => {
  const t = useSec();
  const o = Math.min(fi > 0 ? clamp(t / fi) : 1, fo > 0 ? clamp((len - t) / fo) : 1);
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

export const Bg: React.FC<{tone?: 'char' | 'green' | 'warm' | 'cold' | 'red' | 'black'; glow?: number; gx?: number; gy?: number}> = ({tone = 'char', glow = 0.5, gx = 50, gy = 42}) => {
  const base = {char: ['#222827', '#0c0e0e', '#030404'], green: ['#1d3a2f', '#0b1713', '#030605'], warm: ['#2c2619', '#12100b', '#040403'], cold: ['#1b2226', '#0b0e10', '#030404'], red: ['#2a1213', '#0e0707', '#030303'], black: ['#0b0c0c', '#050606', '#010101']}[tone];
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 95% at ${gx}% ${gy}%, ${base[0]} 0%, ${base[1]} ${40 + glow * 30}%, ${base[2]} 100%)`}} />
  );
};

export const Finish: React.FC<{vig?: number}> = ({vig = 0.55}) => {
  const f = useCurrentFrame();
  const ox = Math.floor(rnd(f) * 512), oy = Math.floor(rnd(f + 99) * 512);
  return (
    <>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 48%, rgba(0,0,0,0) 45%, rgba(0,0,0,${vig}) 100%)`, pointerEvents: 'none'}} />
      <AbsoluteFill style={{backgroundImage: `url(${staticFile('grain.png')})`, backgroundPosition: `${ox}px ${oy}px`, opacity: 0.1, mixBlendMode: 'overlay', pointerEvents: 'none'}} />
    </>
  );
};

export const Kicker: React.FC<{children: React.ReactNode; color?: string; size?: number; style?: React.CSSProperties; track?: number}> = ({children, color = C.gold, size = 22, style, track = 0.38}) => (
  <div style={{fontFamily: SANS, fontWeight: 600, fontSize: size, letterSpacing: `${track}em`, textTransform: 'uppercase', color, ...style}}>{children}</div>
);

export const Serif: React.FC<{children: React.ReactNode; size?: number; color?: string; italic?: boolean; weight?: number; style?: React.CSSProperties}> = ({children, size = 90, color = C.ivory, italic, weight = 500, style}) => (
  <div style={{fontFamily: SERIF, fontWeight: weight, fontStyle: italic ? 'italic' : 'normal', fontSize: size, color, lineHeight: 1.02, ...style}}>{children}</div>
);

/** Text sliding up out of a mask. */
export const Rise: React.FC<{t: number; at: number; dur?: number; children: React.ReactNode; style?: React.CSSProperties; dy?: number}> = ({t, at, dur = 0.8, children, style, dy = 110}) => {
  const p = eo3(prog(t, at, at + dur));
  return (
    <div style={{overflow: 'hidden', paddingBottom: 6, ...style}}>
      <div style={{transform: `translateY(${(1 - p) * dy}%)`, opacity: clamp(p * 3)}}>{children}</div>
    </div>
  );
};

export const Fadein: React.FC<{t: number; at: number; dur?: number; dy?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({t, at, dur = 0.7, dy = 18, children, style}) => {
  const p = eo3(prog(t, at, at + dur));
  return <div style={{opacity: p, transform: `translateY(${(1 - p) * dy}px)`, ...style}}>{children}</div>;
};

export const Rule: React.FC<{t: number; at: number; dur?: number; w: number; color?: string; style?: React.CSSProperties}> = ({t, at, dur = 0.9, w, color = C.gold, style}) => (
  <div style={{height: 2, width: w * eo3(prog(t, at, at + dur)), background: color, ...style}} />
);

/** Chapter title card, bottom-left, shown for ~3s. */
export const ChapterCard: React.FC<{n: string; title: string; sub?: string; len?: number}> = ({n, title, sub, len = 3.2}) => {
  const t = useSec();
  const out = clamp((len - t) / 0.5);
  return (
    <AbsoluteFill style={{opacity: out}}>
      <div style={{position: 'absolute', left: 130, bottom: 150}}>
        <Fadein t={t} at={0.1}>
          <Kicker>{`Chapter ${n}`}</Kicker>
        </Fadein>
        <Rule t={t} at={0.25} w={150} style={{margin: '16px 0 18px'}} />
        <Rise t={t} at={0.35} dur={0.9}>
          <Serif size={84}>{title}</Serif>
        </Rise>
        {sub && (
          <Fadein t={t} at={1.0}>
            <Kicker color={C.ivoryDim} size={18} track={0.3} style={{marginTop: 14}}>
              {sub}
            </Kicker>
          </Fadein>
        )}
      </div>
    </AbsoluteFill>
  );
};

/** "Illustration" tag used wherever a drawing stands in for a photograph. */
export const IllusTag: React.FC<{text?: string}> = ({text = 'Original illustration'}) => (
  <div style={{position: 'absolute', right: 70, bottom: 52}}>
    <Kicker color="rgba(241,233,214,0.38)" size={13} track={0.3}>
      {text}
    </Kicker>
  </div>
);

export const Svg: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
  <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{position: 'absolute', left: 0, top: 0, ...style}}>
    {children}
  </svg>
);

/** Moving speed streaks for racing passes. */
export const Streaks: React.FC<{t: number; y0: number; y1: number; speed?: number; n?: number; seed?: number; color?: string}> = ({t, y0, y1, speed = 2400, n = 26, seed = 1, color = C.ivory}) => (
  <g>
    {Array.from({length: n}).map((_, i) => {
      const y = y0 + rnd(i * 3 + seed) * (y1 - y0);
      const len = 120 + rnd(i * 7 + seed) * 420;
      const sp = speed * (0.5 + rnd(i * 11 + seed));
      const x = ((rnd(i * 5 + seed) * 2400 - t * sp) % 2400 + 2400) % 2400 - 240;
      return <line key={i} x1={x} y1={y} x2={x + len} y2={y} stroke={color} strokeOpacity={0.05 + rnd(i * 13) * 0.14} strokeWidth={1 + rnd(i * 17) * 2} />;
    })}
  </g>
);

export const Flash: React.FC<{t: number; at: number; dur?: number; color?: string; peak?: number}> = ({t, at, dur = 0.25, color = '#fff6dc', peak = 0.9}) => {
  const p = 1 - prog(t, at, at + dur);
  const on = t >= at && t < at + dur;
  return on ? <AbsoluteFill style={{background: color, opacity: p * p * peak, mixBlendMode: 'screen'}} /> : null;
};

export const Counter: React.FC<{v: number; dec?: number; sep?: boolean}> = ({v, dec = 0, sep = true}) => {
  const s = v.toFixed(dec);
  return <>{sep ? Number(s).toLocaleString('en-GB', {minimumFractionDigits: dec, maximumFractionDigits: dec}) : s}</>;
};
