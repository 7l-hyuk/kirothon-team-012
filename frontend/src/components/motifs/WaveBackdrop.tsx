// 연한 바탕 화면용 청해파(물결 비늘) 배경. 레퍼런스 2~4번 화면의 아래쪽 띠, 오른쪽 위 부채꼴.
// 부모에 position: relative + isolation: isolate 가 있어야 글자 뒤로 깔립니다.
import { useId } from "react";

/** 청해파 비늘 좌표. 위 줄부터 그려야 아래 줄이 위 줄을 덮습니다. */
function waveScales(width: number, height: number, R: number) {
  const out: { x: number; y: number }[] = [];
  for (let row = 0; row * (R / 2) <= height + R; row++) {
    const off = row % 2 ? R : 0;
    for (let x = -R + off; x <= width + R; x += R * 2) out.push({ x, y: row * (R / 2) });
  }
  return out;
}

function WaveField({ width, height, R, fill, stroke, mask }: { width: number; height: number; R: number; fill: string; stroke: string; mask: "up" | "corner" }) {
  const id = useId();
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden style={{ display: "block" }}>
      <defs>
        {mask === "up" ? (
          <linearGradient id={`${id}g`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff" stopOpacity="0" />
            <stop offset=".55" stopColor="#fff" stopOpacity=".8" />
            <stop offset="1" stopColor="#fff" stopOpacity="1" />
          </linearGradient>
        ) : (
          <radialGradient id={`${id}g`} cx="1" cy="0" r="1">
            <stop offset="0" stopColor="#fff" stopOpacity="1" />
            <stop offset=".7" stopColor="#fff" stopOpacity=".5" />
            <stop offset="1" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
        )}
        <mask id={`${id}m`}><rect width={width} height={height} fill={`url(#${id}g)`} /></mask>
      </defs>
      <g mask={`url(#${id}m)`}>
        {waveScales(width, height, R).map((p, i) => (
          <g key={i} style={{ stroke }} strokeWidth="1">
            <circle cx={p.x} cy={p.y} r={R} style={{ fill }} />
            <circle cx={p.x} cy={p.y} r={R * 0.7} fill="none" />
            <circle cx={p.x} cy={p.y} r={R * 0.4} fill="none" />
          </g>
        ))}
      </g>
    </svg>
  );
}

export function WaveBackdrop({ variant = "both", fill = "var(--bg)" }: { variant?: "bottom" | "corner" | "both"; fill?: string }) {
  const stroke = "var(--navy-line)";
  return (
    <div className="backdrop" aria-hidden>
      {variant !== "bottom" && (
        <div style={{ right: 0, top: 0, opacity: .55 }}><WaveField width={190} height={170} R={18} fill={fill} stroke={stroke} mask="corner" /></div>
      )}
      {variant !== "corner" && (
        <div style={{ left: 0, right: 0, bottom: 0, opacity: .6 }}><WaveField width={430} height={150} R={26} fill={fill} stroke={stroke} mask="up" /></div>
      )}
    </div>
  );
}
