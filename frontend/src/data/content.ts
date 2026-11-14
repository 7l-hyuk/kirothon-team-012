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

export interface SubmitStep { pre?: string; b?: string; post?: string; sub?: string; btn: string; msg?: string }
export const SUBMIT_STEPS: SubmitStep[] = [
  { pre: "안전신문고에 접속하세요", sub: "safetyreport.go.kr 또는 앱", btn: "안전신문고 열기", msg: "안전신문고를 열었어요" },
  { pre: "로그인하세요", sub: "회원이 아니면 본인인증 후 비회원 신고도 가능합니다", btn: "했어요" },
  { b: "생활불편 신고 > 쓰레기·폐기물", post: " 을 선택하세요", btn: "했어요" },
  { b: "사진", post: " 항목에 아래 2장을 첨부하세요", btn: "사진 저장", msg: "사진 2장을 저장했어요" },
  { b: "발생 위치", post: " 는 지도에서 현재 위치를 확인하세요", btn: "했어요" },
  { b: "내용", post: " 항목에 아래 글을 붙여 넣으세요", btn: "글 복사", msg: "글을 복사했어요" },
  { pre: "제출하고, 접수번호를 알려 주세요 (선택)", btn: "접수 완료" },
];

export const DRAFTS = [
  "서울시 마포구 ○○로 12 앞 전봇대 아래에 종량제 봉투를 쓰지 않은 생활쓰레기가 무단투기되어 있습니다. 2026년 11월 14일 오후 2시경 확인했으며, 악취와 통행 불편이 있어 수거와 단속을 요청드립니다.",
  "서울시 마포구 ○○로 12 앞 전봇대 아래에 생활쓰레기가 무단투기되어 있습니다. 2026년 11월 14일 오후 2시경 확인했습니다. 수거와 단속을 요청드립니다.",
  "안녕하세요. 서울시 마포구 ○○로 12 앞 전봇대 아래에 종량제 봉투를 쓰지 않은 생활쓰레기가 무단투기되어 있어 알려 드립니다. 2026년 11월 14일 오후 2시경 확인했으며, 악취와 통행 불편이 있습니다. 수거와 단속을 부탁드립니다. 감사합니다.",
];

export type MineGroup = "준비 중" | "접수 완료" | "처리 완료";
export interface MineItem { id: number; type: string; place: string; status: string; g: MineGroup; to: string; no: string; cont?: boolean }
export const MINE: MineItem[] = [
  { id: 0, type: "불법주정차 (인도)", place: "마포구 서교동 · 11월 14일", status: "접수 완료", g: "접수 완료", to: "안전신문고 > 불법주정차", no: "입력 안 함" },
  { id: 1, type: "쓰레기 무단투기", place: "마포구 서교동 · 11월 14일", status: "처리 완료 · 수용", g: "처리 완료", to: "안전신문고 > 생활불편", no: "SPP-2611-014273" },
  { id: 2, type: "불법 광고물", place: "마포구 합정동 · 11월 12일", status: "준비 중 · 증거 1/3", g: "준비 중", cont: true, to: "안전신문고 > 생활불편", no: "접수 전" },
];
export const MINE_FILTERS = ["전체", "준비 중", "접수 완료", "처리 완료"] as const;

export interface Article { id: number; title: string; type: string; cat: string; result: string; gu: string; when: string; likes: number; photo: string; sec: string[] }
export const ARTICLES: Article[] = [
  { id: 0, title: "횡단보도 위 주차, 사진 2장으로 과태료 부과까지", type: "불법주정차", cat: "불법주정차", result: "수용", gu: "마포구", when: "2026년 10월", likes: 24, photo: "횡단보도 위 차량 (번호판 가림)",
    sec: ["출근길 횡단보도 위에 승용차가 걸쳐 서 있어 유모차가 차도로 돌아가야 했어요.", "차량 뒤쪽에서 번호판과 횡단보도 선이 함께 보이게 1장, 같은 자리에서 1분 뒤에 1장 더 찍었어요.", "안전신문고 앱의 불법주정차 메뉴에서 횡단보도를 고르고 앱 카메라로 바로 촬영해 제출했어요.", "수용됐고, 과태료 부과 예정이라는 답변을 6일 뒤에 받았어요.", "1분을 기다리는 동안 자리를 옮기지 마세요. 두 장의 구도가 같아야 해요."] },
  { id: 1, title: "처음엔 반려됐어요. 옆모습 사진이 문제였습니다", type: "불법주정차", cat: "불법주정차", result: "불수용 → 재신고 수용", gu: "성동구", when: "2026년 9월", likes: 41, photo: "인도 위 차량 (번호판 가림)",
    sec: ["인도 위에 차가 올라와 있어서 보행자가 차도로 내려가야 했어요.", "처음에는 앞에서 1장, 옆에서 1장을 찍었어요. 두 번째에는 뒤쪽 같은 자리에서 1분 간격으로 2장을 찍었어요.", "안전신문고 앱의 불법주정차 메뉴에서 인도를 고르고 제출했어요.", "첫 신고는 사진 요건 미달로 불수용됐고, 다음 날 다시 신고해 5일 뒤 수용됐어요.", "방향이 다른 사진 2장은 인정되지 않아요. 같은 위치, 같은 방향으로 찍으세요."] },
  { id: 2, title: "전단지 신고, 전화번호 사진이 핵심이었어요", type: "불법 광고물", cat: "광고물", result: "수용", gu: "관악구", when: "2026년 10월", likes: 12, photo: "전봇대 전단지 (전화번호 가림)",
    sec: ["집 앞 전봇대에 대출 전단지가 여러 장 붙어 있었어요.", "전체 사진, 전화번호와 상호가 보이는 근접 사진, 부착 위치가 보이는 원거리 사진 3장을 준비했어요.", "안전신문고 생활불편 신고에서 불법 광고물을 골라 사진 3장과 함께 접수했어요.", "수용됐고, 4일 뒤 철거됐다는 답변을 받았어요.", "전화번호가 또렷하게 찍힌 근접 사진이 있어야 광고주를 확인할 수 있어요."] },
];
export const ARTICLE_HEADS = ["어떤 상황이었나", "어떤 사진을 준비했나", "어디에 어떻게 접수했나", "결과와 걸린 시간", "다음 사람을 위한 팁"];
export const CASE_FILTERS = ["전체", "불법주정차", "쓰레기", "광고물", "시설물"] as const;

export const SHARE_RULES: [string, string][] = [
  ["차량 번호판, 사람 얼굴", "사진에서 가림"],
  ["상세 주소", "구 단위까지만 표시"],
  ["날짜와 시각", "월 단위까지만 표시"],
  ["접수번호, 이름, 연락처", "삭제"],
  ["전단지 속 전화번호·상호", "사진에서 가림"],
];
