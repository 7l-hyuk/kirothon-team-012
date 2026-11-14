# 설계: 프론트 화면 톤 통일

요구사항: `requirements.md`. 동작은 그대로 두고 **토큰 → 공통 CSS → 공통 부품 → 화면 마크업** 순서로 바꾼다. 대부분은 CSS 교체로 해결하고, 화면 파일은 공통 부품을 끼우는 정도로만 고친다.

## 1. 토큰 (`styles/tokens.css`)
기존 변수 이름(`--ink`, `--sub`, `--line`, `--bg`, `--card` 등)은 유지하고 값만 바꾼다. 화면 코드가 이 이름을 직접 쓰고 있어서 이름을 바꾸면 수정 범위가 커진다.

| 변수 | 이전 | 이후 | 쓰임 |
|---|---|---|---|
| `--navy` (신규) | | `#25488a` | 주 버튼, 선택, 아이콘 |
| `--navy-2` (신규) | | `#1f3d78` | 주 버튼 hover |
| `--navy-soft` (신규) | | `#e2e7f3` | 아이콘 원, 약한 버튼 |
| `--ink` | `#1a2140` | `#1b2240` | 본문 글자 |
| `--sub` | `#6b7088` | `#5d6480` | 보조 글자 |
| `--line` | `#e4ddcf` | `#dfe4ef` | 구분선 |
| `--line-strong` | `#cfc5b0` | `#c6cfe2` | 입력 테두리 |
| `--bg` | `#f7f3ea` | `#eef1f8` | 화면 바탕 |
| `--bg-2` | `#efe9db` | `#e6eaf4` | 안내 박스, 눌린 칩 |
| `--chat-bg` | `#f2ede2` | `#eef1f8` | 대화 바탕 |
| `--gold*` | 금색 | `--navy` 계열로 대체 | 진행 표시, 탭 |
| `--shadow` (신규) | | `0 6px 18px rgba(37,72,138,.08)` | 카드 |
| `--r` / `--r-lg` / `--r-xl` | 10 / 12 | 12 / 16 / 22 | 버튼 / 카드 / 큰 카드 |

상태 색(`--ok`, `--warn`, `--mute`)은 그대로 둔다. `landing.css`의 지역 변수는 이 토큰으로 바꾼다.

## 2. 공통 CSS (`styles/global.css`)
- `.btn-primary`: `--navy` 채움. `.btn-outline`: `--navy` 1.5px 테두리. `.btn-secondary`: `--navy-soft` 바탕, 테두리 없음.
- `.panel`, `.bot`, `.resume`, `.item`, `.composer`: 흰 카드 + `--r-lg` + `--shadow`, 테두리는 아주 옅게.
- `.me .bubble`: `--navy` 채움.
- `.chip.on`: `--navy` 채움.
- `.tabs`: 사용하지 않음(하단 탭 제거).
- `.timer` 링: `--navy` 진행.
- `.screen`에 `position: relative; isolation: isolate`를 주고, 배경 문양은 `z-index: -1`로 깐다.

## 3. 공통 부품 (신규)
| 파일 | 내용 |
|---|---|
| `components/icons/Icons.tsx` | 선 아이콘: `Back`, `Home`, `ChevronRight`, `ArrowRight`, `Check`, `Plus`, `Camera`, `Image`, `Search`, `Doc`, `Copy`, `Pencil`, `Car`, `Trash`, `Poster`, `Cone`(시설물), `Help`, `Alert`. 모두 `currentColor`, `aria-hidden` |
| `components/motifs/WaveBackdrop.tsx` | 청해파 물결을 아래쪽 띠와 오른쪽 위 부채꼴로 그린다. `variant="bottom" \| "corner" \| "both"`. `LandingMotifs`의 비늘 그리기를 재사용할 수 있게 `waveScales()` 함수로 분리 |
| `components/motifs/Mascot.tsx` | 갓 쓴 유령. 아래 4절 |
| `components/AppBar.tsx` | 뒤로 가기 / 가운데 제목 / 홈 아이콘. `onBack`, `title`, `right?` |
| `components/Stepper.tsx` | 번호 원 5개와 연결선. 끝난 단계는 체크, 현재 단계는 남색 채움, 현재 단계 이름만 아래에 표시 |

`components/ui`의 `Mark`, `Check`는 글자 기호(✓, !, –) 대신 `Icons`를 쓰도록 바꾼다. 화면이 쓰는 props는 그대로 둔다.

## 4. 화면 크기 (아이폰 14 기준, 비율 대응)
- `index.html`: `viewport-fit=cover`로 노치 영역까지 쓰고, 각 화면이 `env(safe-area-inset-*)`만큼 비켜 앉는다(상단 바, 하단 여백, 타이머, 토스트, S0 위 여백).
- `.viewport > .app` 구조. 폭 600px 미만은 `.app`이 `100% × 100dvh`. 600px 이상은 `390 × 844` 고정 틀을 가운데 두고 `transform: scale(var(--frame-scale))`로 줄인다. `--frame-scale`은 `main.tsx`가 창 크기로 계산한다(최대 1, 최소 0.4).
- `.app`에 `container-type: size`를 주고, 세로로 늘고 줄어야 하는 값은 `cqh`/`cqw`로 쓴다.
  - S0: 위 여백 `clamp(40px, 100cqh - 694px, 150px)`(844에서 150px), 문양 영역은 남는 높이를 차지(최소 140px, 최대 250px). 문양 위치와 크기는 390×230 기준 % 값.
  - S0 제목 `clamp(36px, 11.8cqw, 46px)`, S1 제목 `clamp(20px, 6.6cqw, 26px)` + 줄바꿈 없음.
  - 타이머 원 `min(240px, 30cqh)`.
- 마스코트(갓 쓴 유령)는 사용자 요청으로 뺐다.

## 5. 화면별 변경
### 라우트와 이동
| 경로 | 화면 | 뒤로 가기 | 하단 탭 |
|---|---|---|---|
| `/` | S0 Landing | 없음 | 없음 |
| `/report` | S1 Home | `/` | 없음 |
| `/chat` | 신고 대화 | `goHome()` → `/report` (기존 동작) | 없음 |
| `/done` | S9 | 없음(홈 아이콘만) | 없음 |
| `/mine` | S10 신고 조회 | `/` | 없음 |
| `/mine/:id` | S11 | `/mine` | 없음 |
| `/share` | S14 | 기존 `cancel` | 없음 |
| `/cases` | S12 신고 사례 | `/` | 없음 |
| `/cases/:id` | S13 | `/cases` | 없음 |

`App.tsx`에서 `TabBar`를 뺀다. `TabBar.tsx` 파일은 Git에 올라가기 전이라 지우면 되돌릴 수 없으므로 지우지 않고 import만 뺀다. Landing의 "도움말" 카드는 "신고 사례" 카드(책 아이콘, `/cases`)로 바꾼다. S9에 "홈으로" 버튼(`toLanding`)을 추가한다. S12 목록 끝에 "신고하러 가기" 버튼(`/report`)을 둔다.

`Stepper`의 현재 단계: S1은 0(상황 입력), 신고 대화는 기존 `stage` 계산, S9은 5(전부 체크).

### 화면 마크업
| 화면 | 변경 |
|---|---|
| S0 `Landing` | `landing.css` 색을 토큰으로 교체. "도움말" 카드 → "신고 사례" 카드 |
| S1 `Home` | `AppBar`(제목 "신고하기") + `Stepper`(1단계). 제목 한 줄. 입력 카드(카메라·갤러리 아이콘 버튼). `CHIPS` 대신 `TYPE_CARDS` 2×2(아이콘, 유형 이름, 짧은 설명). 카드 클릭은 기존 칩과 같이 `set({ text, hasPhoto: true })`. 보조 설명·112·119 안내 없음. `WaveBackdrop both` |
| 신고 대화 `Chat` | 상단을 `AppBar`(제목 "신고하기", 오른쪽 건수 표시) + `Stepper`로 교체. 카드·말풍선은 CSS로 처리 |
| `TimerOverlay` | 링 색 `--navy`, 배경 `WaveBackdrop corner` |
| S9 `Done` | `Stepper`(전부 체크). 가운데 큰 체크 원(흰 원 + 남색 체크) + 제목, 건별 요약 카드(문서 아이콘, 접수번호, 번호가 있으면 `복사` 버튼), 공유 권유 카드, 하단 버튼 "내 신고에서 보기"(주) + "홈으로"(보조). `WaveBackdrop both` |
| S10 `Mine` | `AppBar`("신고 조회", 뒤로 → `/`) + 칩. 목록을 카드형으로(사진, 유형, 장소, 상태 pill, 오른쪽 화살표). 빈 상태에 "신고하러 가기" |
| S11 `MineDetail`, S13 `Article`, S14 `Share` | `navrow`를 `AppBar`로 교체 |
| S12 `Cases` | `AppBar`("신고 사례", 뒤로 → `/`). 기존 `Cloud`, `Pine` 장식 제거, `WaveBackdrop corner`. 카드에 그림자. 목록 끝에 "신고하러 가기" |

`content.ts`에 `TYPE_CARDS`를 추가한다. 기존 `CHIPS`는 지우지 않는다(다른 곳에서 쓸 수 있음).

## 6. 하지 않는 것
- 상태(`store.tsx`)와 라우트는 고치지 않는다. 단, AppBar의 홈 아이콘은 `nav("/")`로 이동하기 전에 `goHome`과 같은 정리가 필요하므로 store에 `toLanding()`을 추가한다(타이머·대기 정리 후 `/`).
- 다크 모드, 데스크톱 전용 레이아웃.

## 7. 검증
- `npm run build`.
- `vite preview` + 헤드리스 Chrome 390×844로 화면별 스크린샷. 대화 화면은 `?fast`로 진행.
