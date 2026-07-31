import React from 'react';
import {Composition} from 'remotion';
import {CowartFlow} from './compositions/CowartFlow';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="CowartFlow"
      component={CowartFlow}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
