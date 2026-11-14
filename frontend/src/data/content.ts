/** 목업에 들어 있던 시나리오·목데이터. API 명세가 오면 이 파일의 데이터는 서버 응답으로 대체된다. */

export const CHIPS = [
  "인도에 차가 올라와 있어요",
  "골목에 쓰레기가 쌓여 있어요",
  "전봇대에 전단지가 덕지덕지 붙어 있어요",
  "아파트 주차장에 이중주차가 돼 있어요",
];

export const STAGES = ["상황 입력", "항목 선택", "증거 준비", "접수 안내", "완료"];

/** S1 유형 카드: 신고메이트가 다루는 4개 유형. 누르면 입력창에 일반화한 문장만 채운다(사진은 넣지 않음).
 *  장소나 구역은 일부러 비워 둔다. 사용자가 덧붙이지 않으면 AI가 판단에 필요한 것을 되묻는다(backend/app/ai/prompts/analyze_system.md). */
export type TypeIcon = "car" | "trash" | "poster" | "cone";
export const TYPE_CARDS: { icon: TypeIcon; title: string; desc: string; example: string }[] = [
  { icon: "car", title: "불법주정차", desc: "인도, 횡단보도, 소화전 앞 등", example: "불법주정차된 차가 있어요" },
  { icon: "trash", title: "쓰레기 무단투기", desc: "골목, 전봇대 아래 쓰레기", example: "쓰레기가 무단으로 버려져 있어요" },
  { icon: "poster", title: "불법 광고물", desc: "전단지, 현수막", example: "불법 광고물이 붙어 있어요" },
  { icon: "cone", title: "시설물 파손", desc: "보도블록, 가로등 등", example: "도로나 시설물이 파손돼 있어요" },
];

export const MINE_FILTERS = ["전체", "준비 중", "접수 완료", "처리 완료"] as const;

export const CASE_FILTERS = ["전체", "불법주정차", "쓰레기", "광고물", "시설물"] as const;
