import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import theme from '../theme.json';

const ink = theme.palette.ink;
const paper = theme.palette.paper;
const yellow = theme.palette.accent;

const clamp = {
  extrapolateLeft: 'clamp' as const,
  extrapolateRight: 'clamp' as const,
};

const useEntrance = (from: number, duration = 18) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({
    frame: frame - from,
    fps,
    durationInFrames: duration,
    config: {damping: 17, stiffness: 180, mass: 0.7},
  });
};

const PuzzleIcon: React.FC = () => (
  <svg viewBox="0 0 64 64" width="60" height="60">
    <path
      d="M14 21h13c-3-9 12-9 9 0h14v13c9-3 9 12 0 9v9H36c3-9-12-9-9 0H14V39c-9 3-9-12 0-9Z"
      fill="none"
      stroke="white"
      strokeWidth="5"
      strokeLinejoin="round"
    />
  </svg>
);

const ServiceIcon: React.FC = () => (
  <svg viewBox="0 0 64 64" width="60" height="60">
    <path d="M13 13h38v14H25v10h26v14H13V37h12V27H13Z" fill="none" stroke="white" strokeWidth="5" />
    <path d="m43 18 8 2-8 2M21 42l-8 2 8 2" fill="none" stroke="white" strokeWidth="4" />
  </svg>
);

const McpIcon: React.FC = () => (
  <svg viewBox="0 0 64 64" width="56" height="56">
    <path
      d="M20 39 38 21c8-8 19 4 11 12L31 51c-12 12-28-5-17-16l17-17c7-7 17 4 10 11L25 45c-3 3-8-2-5-5l14-14"
      fill="none"
      stroke="white"
      strokeWidth="5"
      strokeLinecap="round"
    />
  </svg>
);

const Card: React.FC<{
  x: number;
  y: number;
  width?: number;
  label: string;
  start: number;
  icon: React.ReactNode;
}> = ({x, y, width = 250, label, start, icon}) => {
  const p = useEntrance(start);
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width,
        height: 160,
        background: paper,
        border: `5px solid ${ink}`,
        boxShadow: `15px 15px 0 ${ink}`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        opacity: p,
        transform: `translateY(${(1 - p) * 38}px) scale(${0.82 + p * 0.18})`,
      }}
    >
      <div
        style={{
          width: 72,
          height: 72,
          display: 'grid',
          placeItems: 'center',
          background: ink,
          marginBottom: 8,
        }}
      >
        {icon}
      </div>
      <div style={{fontSize: 34, fontWeight: 850}}>{label}</div>
    </div>
  );
};

const Line: React.FC<{
  x: number;
  y: number;
  width: number;
  start: number;
  vertical?: boolean;
}> = ({x, y, width, start, vertical = false}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [start, start + 18], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: vertical ? 10 : width,
        height: vertical ? width : 10,
        background: yellow,
        transformOrigin: vertical ? 'center top' : 'left center',
        transform: vertical ? `scaleY(${p})` : `scaleX(${p})`,
      }}
    />
  );
};

const Header: React.FC = () => {
  const p = useEntrance(0);
  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: 120,
          top: 84,
          width: 410,
          height: 92,
          background: ink,
          color: paper,
          padding: '0 32px',
          display: 'flex',
          alignItems: 'center',
          fontSize: 58,
          fontWeight: 900,
          boxShadow: `12px 12px 0 ${ink}`,
          transformOrigin: 'left center',
          transform: `scaleX(${p})`,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
        }}
      >
        怎么解决
      </div>
      <div
        style={{
          position: 'absolute',
          left: 120,
          top: 205,
          width: 150,
          height: 56,
          background: yellow,
          border: `5px solid ${ink}`,
          boxShadow: `8px 8px 0 ${ink}`,
          display: 'grid',
          placeItems: 'center',
          fontSize: 27,
          fontWeight: 900,
          opacity: p,
          transform: `translateY(${(1 - p) * 16}px)`,
        }}
      >
        LINK
      </div>
    </>
  );
};

const GithubPanel: React.FC = () => {
  const frame = useCurrentFrame();
  const enter = useEntrance(20, 22);
  const exit = interpolate(frame, [92, 112], [1, 0], clamp);
  return (
    <div
      style={{
        position: 'absolute',
        left: 695,
        top: 445,
        width: 700,
        height: 160,
        background: '#090c12',
        color: 'white',
        display: 'flex',
        alignItems: 'center',
        gap: 30,
        padding: '0 46px',
        boxShadow: `14px 14px 0 ${ink}`,
        opacity: enter * exit,
        transform: `translateX(${(1 - enter) * 80}px)`,
      }}
    >
      <div style={{fontSize: 78}}>●</div>
      <div style={{fontSize: 43, fontWeight: 700}}>
        zhongerxin <span style={{opacity: 0.65, margin: '0 24px'}}>/</span> Cowart
      </div>
      <div style={{marginLeft: 'auto', fontSize: 32}}>▼</div>
    </div>
  );
};

const BottomBadge: React.FC = () => {
  const p = useEntrance(235);
  return (
    <div
      style={{
        position: 'absolute',
        left: 645,
        top: 820,
        width: 630,
        height: 72,
        border: `5px solid ${ink}`,
        boxShadow: `12px 12px 0 ${ink}`,
        background: yellow,
        display: 'grid',
        placeItems: 'center',
        fontSize: 37,
        fontWeight: 900,
        opacity: p,
        transform: `translateY(${(1 - p) * 28}px) scale(${0.9 + p * 0.1})`,
      }}
    >
      MCP 关联
    </div>
  );
};

const Presenter: React.FC = () => {
  const frame = useCurrentFrame();
  const bob = Math.sin(frame / 15) * 3;
  return (
    <div
      style={{
        position: 'absolute',
        left: 92,
        bottom: 58 + bob,
        width: 250,
        height: 250,
        borderRadius: '50%',
        border: `7px solid ${paper}`,
        background: 'linear-gradient(145deg, #d4c5b8, #8e745f)',
        boxShadow: `8px 10px 0 ${ink}`,
        display: 'grid',
        placeItems: 'center',
        overflow: 'hidden',
      }}
    >
      <div style={{fontSize: 36, fontWeight: 900, color: paper, textAlign: 'center'}}>
        YOUR
        <br />
        VIDEO
      </div>
    </div>
  );
};

const Subtitle: React.FC = () => {
  const frame = useCurrentFrame();
  const text =
    frame < 95
      ? '大佬开源了一个无线画板项目'
      : frame < 205
        ? '在本地启动一个无限画板的服务'
        : '将本地服务与 Codex 进行关联';
  const pop = spring({
    frame: frame % 100,
    fps: 30,
    config: {damping: 18, stiffness: 170},
  });
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 56,
        left: '50%',
        transform: `translateX(-50%) scale(${0.96 + pop * 0.04})`,
        padding: '14px 26px',
        color: 'white',
        background: 'rgba(57,54,48,0.78)',
        borderRadius: 18,
        fontSize: 39,
        fontWeight: 650,
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </div>
  );
};

export const CowartFlow: React.FC = () => {
  const frame = useCurrentFrame();
  const backgroundImage =
    theme.background.mode === 'image' && theme.background.image
      ? `linear-gradient(rgba(255,250,240,${theme.background.overlayOpacity}), rgba(255,250,240,${theme.background.overlayOpacity})), url("${staticFile(theme.background.image)}")`
      : theme.background.mode === 'grid'
        ? 'linear-gradient(rgba(191,164,109,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(191,164,109,.12) 1px, transparent 1px)'
        : 'none';
  const projectX = interpolate(frame, [95, 125], [520, 245], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const showFlow = interpolate(frame, [100, 120], [0, 1], clamp);

  return (
    <AbsoluteFill
      style={{
        color: ink,
        fontFamily:
          '"PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif',
        backgroundColor: theme.background.color,
        backgroundImage,
        backgroundSize:
          theme.background.mode === 'image'
            ? theme.background.fit
            : `${theme.background.gridSize}px ${theme.background.gridSize}px`,
        backgroundPosition: theme.background.position,
        backgroundRepeat: theme.background.mode === 'image' ? 'no-repeat' : 'repeat',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 42,
          border: `6px solid ${ink}`,
          boxShadow: `18px 18px 0 ${ink}`,
        }}
      />
      <Header />

      <div style={{position: 'absolute', left: projectX - 520, top: 0}}>
        <Card x={520} y={445} label="开源项目" start={10} icon={<PuzzleIcon />} />
      </div>
      <GithubPanel />

      <div style={{opacity: showFlow}}>
        <Line x={510} y={585} width={360} start={128} />
        <Card x={790} y={505} width={320} label="本地服务" start={145} icon={<ServiceIcon />} />
        <Line x={1108} y={585} width={400} start={170} />

        <div
          style={{
            position: 'absolute',
            left: 1450,
            top: 505,
            width: 280,
            height: 160,
            background: ink,
            color: paper,
            boxShadow: `15px 15px 0 ${theme.palette.shadow}`,
            display: 'grid',
            placeItems: 'center',
            fontSize: 51,
            fontWeight: 950,
            opacity: useEntrance(190),
            transform: `scale(${0.8 + useEntrance(190) * 0.2})`,
          }}
        >
          CODEX
        </div>

        <Line x={945} y={372} width={135} start={205} vertical />
        <Card x={820} y={270} label="MCP" start={218} icon={<McpIcon />} />
        <BottomBadge />
      </div>

      <Presenter />
      <Subtitle />
    </AbsoluteFill>
  );
};
