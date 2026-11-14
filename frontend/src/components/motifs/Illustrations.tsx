// 남색 톤 일러스트. 신고 불가 결과, 빈 목록에 씁니다. 모두 장식이라 aria-hidden.
const NAVY = "#25488a", SOFT = "#e2e7f3", LINE = "#b9c4dc", INK = "#1b2240";

/** 신고 불가: 단지 안 주차장(사유지) 표지와 금지 원 */
export function NotReportableArt({ width = 180 }: { width?: number }) {
  return (
    <svg width={width} height={width * 0.6} viewBox="0 0 180 108" aria-hidden>
      <ellipse cx="90" cy="100" rx="72" ry="6" fill={SOFT} />
      {/* 건물(단지) */}
      <path d="M22 98V40l34-16 34 16v58" fill="#fff" stroke={LINE} strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M34 52h10M34 64h10M34 76h10M68 52h10M68 64h10M68 76h10" stroke={LINE} strokeWidth="3" strokeLinecap="round" />
      <path d="M48 98V82h16v16" fill={SOFT} stroke={LINE} strokeWidth="1.6" />
      {/* 주차 표지 */}
      <path d="M118 98V58" stroke={INK} strokeWidth="2.4" strokeLinecap="round" />
      <rect x="104" y="30" width="28" height="30" rx="6" fill={NAVY} />
      <path d="M113 52V38h6a4.5 4.5 0 0 1 0 9h-6" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      {/* 금지 원 */}
      <circle cx="150" cy="40" r="15" fill="#fff" stroke="#8b93a0" strokeWidth="3" />
      <path d="M139.5 50.5l21-21" stroke="#8b93a0" strokeWidth="3" strokeLinecap="round" />
      {/* 구름 */}
      <path d="M120 16h30M128 22h28" stroke={LINE} strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

/** 빈 목록: 비어 있는 문서와 돋보기 */
export function EmptyListArt({ width = 150 }: { width?: number }) {
  return (
    <svg width={width} height={width * 0.75} viewBox="0 0 160 120" aria-hidden>
      <ellipse cx="80" cy="110" rx="60" ry="6" fill={SOFT} />
      <rect x="44" y="14" width="62" height="82" rx="8" fill="#fff" stroke={LINE} strokeWidth="1.6" />
      <path d="M56 34h38M56 46h30M56 58h34" stroke={SOFT} strokeWidth="5" strokeLinecap="round" />
      <circle cx="104" cy="76" r="17" fill="#fff" stroke={NAVY} strokeWidth="4" />
      <path d="M116.5 88.5L130 102" stroke={NAVY} strokeWidth="5" strokeLinecap="round" />
      <path d="M22 28h18M14 36h22M122 22h20M130 30h16" stroke={LINE} strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
