/** 한국적 모티프 SVG — 보름달, 산 능선, 구름, 소나무 가지, 토끼 실루엣.
 *  모두 currentColor / CSS 변수 기반이라 테마에 따라 색이 바뀐다. */

export function Moon({ size = 120, glow = true }: { size?: number; glow?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden>
      <defs>
        <radialGradient id="moonFill" cx="40%" cy="35%" r="70%">
          <stop offset="0" stopColor="#F3E3AE" />
          <stop offset="0.6" stopColor="#D9B86A" />
          <stop offset="1" stopColor="#B8923A" />
        </radialGradient>
        <radialGradient id="moonGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0.55" stopColor="#F0DFA8" stopOpacity="0.55" />
          <stop offset="1" stopColor="#F0DFA8" stopOpacity="0" />
        </radialGradient>
      </defs>
      {glow && <circle cx="60" cy="60" r="60" fill="url(#moonGlow)" />}
      <circle cx="60" cy="60" r="42" fill="url(#moonFill)" />
    </svg>
  );
}

export function Mountains({ width = 320, height = 90 }: { width?: number; height?: number }) {
  return (
    <svg width={width} height={height} viewBox="0 0 320 90" preserveAspectRatio="none" aria-hidden>
      <path d="M0 70 L60 30 L110 58 L170 18 L230 52 L280 34 L320 60 L320 90 L0 90 Z" fill="#2B3560" />
      <path d="M0 70 L60 30 L110 58 L170 18 L230 52 L280 34 L320 60" fill="none" stroke="#C9A24A" strokeWidth="1.2" />
      <path d="M0 82 L50 60 L120 78 L190 50 L260 72 L320 58 L320 90 L0 90 Z" fill="#1A2140" />
    </svg>
  );
}

export function Cloud({ size = 56, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size * 0.5} viewBox="0 0 56 28" fill="none" stroke={color} strokeWidth="1.3" aria-hidden>
      <path d="M8 22 Q2 22 2 16 Q2 10 9 11 Q10 4 18 5 Q24 1 29 7 Q36 3 39 10 Q47 8 48 15 Q54 16 52 22 Z" />
      <path d="M14 15 q3 -4 6 0 q3 -4 6 0" opacity="0.6" />
    </svg>
  );
}

export function Pine({ size = 72, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size * 0.6} viewBox="0 0 72 43" fill="none" stroke={color} strokeWidth="1.2" strokeLinecap="round" aria-hidden>
      <path d="M2 38 Q24 34 44 22 T70 8" />
      <path d="M28 30 q-4 -8 -2 -14 M30 29 q2 -9 8 -12 M32 29 q6 -6 12 -6" />
      <path d="M50 18 q-4 -7 -1 -12 M52 17 q3 -8 9 -10 M54 17 q6 -5 11 -4" />
      <path d="M14 36 q-3 -5 -1 -9 M16 36 q2 -6 6 -7" />
    </svg>
  );
}

export function Rabbit({ size = 28, color = "currentColor" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill={color} aria-hidden>
      <path d="M9 6 c-1 -4 1 -6 2 -5 c1 1 1 4 1 6 c1 -3 2 -6 4 -6 c1 0 0 4 -1 7 c3 1 6 4 6 8 c0 4 -3 7 -8 7 H8 c-3 0 -5 -2 -5 -5 c0 -2 1 -3 2 -4 c0 -3 2 -6 4 -8 Z" />
      <circle cx="21" cy="22" r="2.2" />
    </svg>
  );
}

/** 토끼가 달 아래 앉은 로고 마크 */
export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <circle cx="16" cy="14" r="11" fill="#D9B86A" />
      <path d="M0 32 L8 22 L14 27 L22 19 L32 28 L32 32 Z" fill="#F6F1E7" />
      <path d="M13 16 c-0.6 -2.4 0.6 -3.6 1.2 -3 c0.6 0.6 0.6 2.4 0.6 3.6 c0.6 -1.8 1.2 -3.6 2.4 -3.6 c0.6 0 0 2.4 -0.6 4.2 c1.8 0.6 3.6 2.4 3.6 4.8 H12 c-1.8 0 -3 -1.2 -3 -3 c0 -1.5 1 -2.6 2 -3 c0 -0.1 0 -0.1 0 0 Z" fill="#1A2140" />
    </svg>
  );
}
