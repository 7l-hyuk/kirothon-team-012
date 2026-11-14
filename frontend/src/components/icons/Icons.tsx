// 선 아이콘. 모두 currentColor, 장식용(aria-hidden). 버튼에는 aria-label을 따로 붙입니다.
import type { ReactNode } from "react";

type P = { size?: number; stroke?: number };

const Svg = ({ size = 24, stroke = 2, children }: P & { children: ReactNode }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    {children}
  </svg>
);

export const Back = (p: P) => <Svg {...p}><path d="M15 5l-7 7 7 7" /></Svg>;
export const ChevronRight = (p: P) => <Svg {...p}><path d="M9 6l6 6-6 6" /></Svg>;
export const ArrowRight = (p: P) => <Svg {...p}><path d="M4 12h15M13 6l6 6-6 6" /></Svg>;
export const Home = (p: P) => <Svg {...p}><path d="M3.5 11L12 4l8.5 7" /><path d="M6 9.5V20h4.5v-5.5h3V20H18V9.5" /></Svg>;
export const Check = (p: P) => <Svg {...p}><path d="M5 12.5l4.5 4.5L19 7.5" /></Svg>;
export const Plus = (p: P) => <Svg {...p}><path d="M12 5v14M5 12h14" /></Svg>;
export const Minus = (p: P) => <Svg {...p}><path d="M6 12h12" /></Svg>;
export const Close = (p: P) => <Svg {...p}><path d="M6.5 6.5l11 11M17.5 6.5l-11 11" /></Svg>;
export const Bang = (p: P) => <Svg {...p}><path d="M12 6v8" /><path d="M12 18h.01" /></Svg>;
export const Camera = (p: P) => <Svg {...p}><path d="M4 8h3l1.6-2.5h6.8L17 8h3v11H4z" /><circle cx="12" cy="13.5" r="3.5" /></Svg>;
export const Gallery = (p: P) => <Svg {...p}><rect x="3.5" y="4.5" width="17" height="15" rx="2.5" /><circle cx="9" cy="10" r="1.6" /><path d="M20.5 16l-5-5L6 19.5" /></Svg>;
export const Search = (p: P) => <Svg {...p}><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5L20 20" /></Svg>;
export const Doc = (p: P) => <Svg {...p}><path d="M6 3.5h8l4 4V20.5H6z" /><path d="M14 3.5v4h4M9 12h6M9 16h4" /></Svg>;
export const Copy = (p: P) => <Svg {...p}><rect x="8.5" y="8.5" width="11" height="11" rx="2" /><path d="M15.5 8.5V5.5a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 5.5V14A1.5 1.5 0 0 0 6 15.5h2.5" /></Svg>;
export const Share = (p: P) => <Svg {...p}><circle cx="18" cy="5.5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="18.5" r="2.5" /><path d="M8.2 10.8l7.6-4.1M8.2 13.2l7.6 4.1" /></Svg>;
export const Heart = (p: P) => <Svg {...p}><path d="M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.4 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z" /></Svg>;
export const Alert = (p: P) => <Svg {...p}><path d="M12 3.5L21.5 20h-19z" /><path d="M12 10v4.5M12 17.2h.01" /></Svg>;
export const Clock = (p: P) => <Svg {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></Svg>;
export const Book = (p: P) => <Svg {...p}><path d="M4 5.5A2 2 0 0 1 6 3.5h13v14H6a2 2 0 0 0-2 2z" /><path d="M4 19.5a2 2 0 0 0 2 2h13v-4" /></Svg>;
export const Shield = (p: P) => <Svg {...p}><path d="M12 3l7.5 3v5.5c0 4.6-3.2 8.1-7.5 9.5-4.3-1.4-7.5-4.9-7.5-9.5V6z" /><path d="M8.8 12.2l2.2 2.2 4.2-4.4" /></Svg>;

/* 유형 아이콘 */
export const Car = (p: P) => <Svg {...p}><path d="M5 16.5V12l1.8-4.6A2 2 0 0 1 8.7 6h6.6a2 2 0 0 1 1.9 1.4L19 12v4.5" /><path d="M3.5 12h17v4.5h-17z" /><path d="M6.5 16.5V19M17.5 16.5V19" /><circle cx="7.5" cy="14.2" r=".6" /><circle cx="16.5" cy="14.2" r=".6" /></Svg>;
export const Trash = (p: P) => <Svg {...p}><path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13" /><path d="M10 11v5.5M14 11v5.5" /></Svg>;
export const Poster = (p: P) => <Svg {...p}><path d="M5 3.5h14v17H5z" /><path d="M8.5 8h7M8.5 11.5h7M8.5 15h4" /><path d="M12 3.5V2" /></Svg>;
export const Cone = (p: P) => <Svg {...p}><path d="M10 4h4l4.5 15h-13z" /><path d="M8.3 10h7.4M7.1 14.5h9.8M3.5 19h17" /></Svg>;
