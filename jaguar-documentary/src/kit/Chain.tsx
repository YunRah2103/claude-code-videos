import React from 'react';
import {C, SANS, SERIF} from '../theme';
import {eo3, prog} from './anim';

export type Link = {name: string; year: string; note?: string; at: number; tone?: 'gold' | 'red' | 'ivory'};

/** Ownership chain: boxes joined by drawn arrows, revealing at their `at` times. */
export const Chain: React.FC<{t: number; links: Link[]; x: number; y: number; w?: number; h?: number; gap?: number}> = ({t, links, x, y, w = 330, h = 170, gap = 110}) => (
  <>
    {links.map((l, i) => {
      const bx = x + i * (w + gap);
      const p = eo3(prog(t, l.at, l.at + 0.7));
      const col = l.tone === 'red' ? C.redLite : l.tone === 'ivory' ? C.silverLite : C.goldLite;
      const ap = i > 0 ? eo3(prog(t, l.at - 0.5, l.at + 0.1)) : 0;
      return (
        <React.Fragment key={l.name + l.year}>
          {i > 0 && (
            <div style={{position: 'absolute', left: bx - gap + 12, top: y + h / 2 - 1, width: (gap - 24) * ap, height: 2, background: C.ivory, opacity: 0.7}}>
              <div style={{position: 'absolute', right: -2, top: -5, width: 0, height: 0, borderLeft: `10px solid ${C.ivory}`, borderTop: '6px solid transparent', borderBottom: '6px solid transparent', opacity: ap > 0.95 ? 1 : 0}} />
            </div>
          )}
          <div style={{position: 'absolute', left: bx, top: y, width: w, height: h, border: `1.5px solid ${col}`, background: 'rgba(0,0,0,0.35)', opacity: p, transform: `translateY(${(1 - p) * 26}px)`, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center'}}>
            <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 15, letterSpacing: '0.34em', color: col, textTransform: 'uppercase'}}>{l.year}</div>
            <div style={{fontFamily: SERIF, fontWeight: 600, fontSize: 44, color: C.ivory, lineHeight: 1.05, marginTop: 10, padding: '0 14px'}}>{l.name}</div>
            {l.note && <div style={{fontFamily: SANS, fontWeight: 500, fontSize: 14, letterSpacing: '0.14em', color: C.ivoryDim, marginTop: 10, textTransform: 'uppercase'}}>{l.note}</div>}
          </div>
        </React.Fragment>
      );
    })}
  </>
);
