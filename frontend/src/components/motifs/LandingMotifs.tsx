// 홈(Landing) 화면 장식: 창살 모서리, 구름, 청해파 원, 卍자문 원, 꽃, 아치.
// 모두 장식용이라 aria-hidden.
import { useId } from "react";

const LINE = "rgba(255,255,255,.55)";

/** 창살 모서리. 왼쪽 위 기준으로 그리고, flip으로 방향을 바꿉니다. */
export function LatticeCorner({ size = 56, color = LINE, flipX = false, flipY = false }: { size?: number; color?: string; flipX?: boolean; flipY?: boolean }) {
  const t = `scale(${flipX ? -1 : 1} ${flipY ? -1 : 1})`;
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" aria-hidden style={{ transform: t }}>
      <g fill="none" stroke={color} strokeWidth="1.2">
        <path d="M1 56V1H56" />
        <path d="M5 46V5H48" />
        <path d="M5 13H22V5 M13 5V22H5 M5 30H13V22 M22 13V22H13 M30 5V13H22" />
        <path d="M30 13H40V5 M5 38H13V30" />
      </g>
    </svg>
  );
}

/** 구름 띠: 둥근 막대 두 개와 가로선. */
export function CloudBand({ width = 90, color = LINE, mirror = false }: { width?: number; color?: string; mirror?: boolean }) {
  return (
    <svg width={width} height={width * 0.33} viewBox="0 0 90 30" aria-hidden style={{ transform: mirror ? "scaleX(-1)" : undefined }}>
      <g fill="none" stroke={color} strokeWidth="1.2" strokeLinecap="round">
        <rect x="28" y="2" width="56" height="9" rx="4.5" />
        <rect x="2" y="13" width="44" height="9" rx="4.5" />
        <path d="M46 17.5H70 M14 27H40" />
      </g>
    </svg>
  );
}

/** 청해파(물결 비늘) 무늬를 원 안에 채웁니다. 위 줄부터 그려 아래 줄이 덮습니다. */
export function WaveCircle({ size = 124, bg = "#25488a", color = "rgba(255,255,255,.5)" }: { size?: number; bg?: string; color?: string }) {
  const id = useId();
  const R = 16;
  const scales: { x: number; y: number }[] = [];
  for (let row = 0; row * (R / 2) <= 124 + R; row++) {
    const off = row % 2 ? R : 0;
    for (let x = -R + off; x <= 124 + R; x += R * 2) scales.push({ x, y: row * (R / 2) });
  }
  return (
    <svg width={size} height={size} viewBox="0 0 124 124" aria-hidden>
      <defs><clipPath id={id}><circle cx="62" cy="62" r="61" /></clipPath></defs>
      <g clipPath={`url(#${id})`}>
        {scales.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={R} fill={bg} stroke={color} strokeWidth="1" />
            <circle cx={p.x} cy={p.y} r={R * 0.68} fill="none" stroke={color} strokeWidth="1" />
            <circle cx={p.x} cy={p.y} r={R * 0.36} fill="none" stroke={color} strokeWidth="1" />
          </g>
        ))}
      </g>
    </svg>
  );
}

/** 卍자문(만자 연속무늬)을 45도 돌려 원 안에 채웁니다. */
export function FretCircle({ size = 124, color = "rgba(255,255,255,.5)" }: { size?: number; color?: string }) {
  const id = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 124 124" aria-hidden>
      <defs>
        <pattern id={`${id}p`} width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45 62 62)">
          <path d="M7 1V13 M1 7H13 M7 1H12 M13 7V12 M7 13H2 M1 7V2" fill="none" stroke={color} strokeWidth="1.3" />
        </pattern>
        <clipPath id={`${id}c`}><circle cx="62" cy="62" r="61" /></clipPath>
      </defs>
      <rect width="124" height="124" fill={`url(#${id}p)`} clipPath={`url(#${id}c)`} />
    </svg>
  );
}

/** 여덟 잎 꽃. */
export function Flower({ size = 46 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 46 46" aria-hidden>
      <g transform="translate(23 23)">
        {Array.from({ length: 8 }, (_, i) => (
          <ellipse key={i} cx="0" cy="-12.5" rx="5.6" ry="10" fill="#dfe5f2" stroke="#9fb0d3" strokeWidth=".8" transform={`rotate(${i * 45})`} />
        ))}
        <circle r="7" fill="#dfe5f2" stroke="#7d93c2" strokeWidth="1.2" />
        <circle r="4" fill="none" stroke="#7d93c2" strokeWidth="1" />
      </g>
    </svg>
  );
}

/** 세 겹 아치. 아래쪽이 열린 ∩ 모양. */
export function Arch({ width = 90, color = LINE }: { width?: number; color?: string }) {
  const h = width * 0.85;
  const arch = (inset: number) => {
    const r = width / 2 - inset;
    return `M${inset} ${h} V${r + inset} A${r} ${r} 0 0 1 ${width - inset} ${r + inset} V${h}`;
  };
  return (
    <svg width={width} height={h} viewBox={`0 0 ${width} ${h}`} aria-hidden>
      <g fill="none" stroke={color} strokeWidth="1.2">
        <path d={arch(1)} />
        <path d={arch(width * 0.11)} />
        <path d={arch(width * 0.22)} />
      </g>
    </svg>
  );
}
