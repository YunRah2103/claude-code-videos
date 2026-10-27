import React from 'react';
import {AbsoluteFill, Audio, staticFile} from 'remotion';
import {Finish} from './kit/Stage';
import {Hook} from './scenes/Hook';
import {Ch1} from './scenes/Ch1';
import {Ch2} from './scenes/Ch2';
import {Ch3} from './scenes/Ch3';
import {Ch4} from './scenes/Ch4';
import {Ch5} from './scenes/Ch5';
import {Ch6} from './scenes/Ch6';
import {C} from './theme';
import {fontCss} from './kit/fonts';

export const Doc: React.FC<{preview?: boolean}> = ({preview}) => (
  <AbsoluteFill style={{background: C.black}}>
    <style>{fontCss}</style>
    <Hook />
    <Ch1 />
    <Ch2 />
    <Ch3 />
    <Ch4 />
    <Ch5 />
    <Ch6 />
    <Finish />
    {!preview && <Audio src={staticFile('audio/mix.m4a')} />}
  </AbsoluteFill>
);
