import React from 'react';
import {Composition, Still} from 'remotion';
import {Thumb} from './Thumb';
import {Doc} from './Doc';
import {TOTAL_FRAMES} from './timing';

export const Root: React.FC = () => (
  <>
    <Composition id="Doc" component={Doc} width={1920} height={1080} fps={30} durationInFrames={TOTAL_FRAMES} defaultProps={{preview: true}} />
    <Still id="Thumb" component={Thumb} width={1920} height={1080} />
  </>
);
