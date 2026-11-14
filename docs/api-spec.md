# 신고메이트 백엔드 API 명세

- 기준: Claude Design 목업 `ShingoMate Board` (S1~S14), `.kiro/steering/structure.md`의 API 경로 초안
- 서버: FastAPI, 모든 경로는 `/api` 아래
- 상태: 초안. 구현하면서 바뀐 부분은 이 문서를 먼저 고칩니다.

## 1. 공통 규칙

### 요청

| 항목 | 규칙 |
|---|---|
| 기기 식별 | 모든 요청에 `X-Device-Id: <UUID v4>` 헤더. 프론트가 첫 접속 때 만들어 localStorage에 저장합니다. 없거나 형식이 틀리면 `400` |
| 본문 형식 | 기본은 `application/json`. 사진이 들어가는 요청만 `multipart/form-data` |
| 사진 | JPEG, PNG, WebP. 장당 10MB 이하. 한 요청에 최대 4장 |
| 시각 | ISO 8601, KST 오프셋 포함 (`2026-11-14T14:02:00+09:00`) |
| ID | 모두 UUID 문자열 |

### 오류 응답

모든 오류는 같은 형태입니다. `detail`은 화면에 그대로 보여 줄 수 있는 해요체 문구입니다.

```json
{ "detail": "사진이 너무 커요. 10MB 이하로 올려 주세요.", "code": "photo_too_large" }
```

| 상태 | `code` | 상황 |
|---|---|---|
| 400 | `missing_device_id` | `X-Device-Id` 헤더 없음 또는 형식 오류 |
| 404 | `not_found` | 없는 리소스이거나 다른 기기의 리소스 |
| 409 | `invalid_state` | 현재 상태에서 할 수 없는 동작 (예: 접수 전 건을 공유) |
| 413 | `photo_too_large` | 사진 용량 초과 |
| 415 | `unsupported_media` | 지원하지 않는 파일 형식 |
| 422 | `validation_error` | 필드 값 오류 |
| 422 | `ai_refused` | AI가 응답을 거절함. "다시 시도해 주세요" 안내 |
| 429 | `daily_limit_exceeded` | 기기당 하루 AI 호출 상한 초과 |
| 502 | `ai_unavailable` | AI 호출 실패 또는 시간 초과 |

다른 기기의 리소스는 `403`이 아니라 `404`로 응답합니다. 리소스가 있는지 알려 주지 않기 위해서입니다.

### AI를 호출하는 엔드포인트

아래 다섯 개가 AI를 호출하며, 기기당 하루 호출 상한(`AI_DAILY_LIMIT`)에 포함됩니다.

- `POST /api/analyses`
- `POST /api/reports/{id}/photos` (`scene_id`를 함께 보낸 경우)
- `POST /api/reports/{id}/rehearsals`
- `POST /api/reports/{id}/drafts`
- `GET /api/reports/{id}/case-preview`

응답 시간이 수 초 걸릴 수 있으므로 프론트는 S2 같은 진행 표시를 보여 줍니다.

### 공통 값

| 이름 | 값 |
|---|---|
| `type_id` | `illegal_parking`(불법주정차), `trash_dumping`(쓰레기 무단투기), `illegal_ad`(불법 광고물), `facility_damage`(도로·시설물 파손) |
| `category` | `report`(신고), `complaint`(민원) |
| 신고 건 `status` | `preparing`(준비 중), `filed`(접수 완료), `resolved`(처리 완료) |
| 처리 `result` | `accepted`(수용), `rejected`(불수용), `unknown`(아직 모름) |
| 검수 `review.status` | `sufficient`(충분), `insufficient`(불충분), `undetermined`(판단 불가) |

---

## 2. 엔드포인트 목록

| 메서드 | 경로 | 용도 | 화면 |
|---|---|---|---|
| POST | `/api/analyses` | 사진·글로 상황 분석, 신고 항목 제안 | S1, S2, S3 |
| GET | `/api/analyses/{id}` | 분석 결과 다시 조회 | S3 |
| POST | `/api/analyses/{id}/reports` | 선택한 항목으로 신고 건 생성 | S3 |
| GET | `/api/reports` | 내 신고 목록 | S1, S10 |
| GET | `/api/reports/{id}` | 내 신고 상세 | S9, S11 |
| PATCH | `/api/reports/{id}` | 진행 단계, 접수번호, 처리 결과 수정 | S7, S11 |
| GET | `/api/reports/{id}/evidence` | 증거 체크리스트와 장면별 상태 | S4 |
| POST | `/api/reports/{id}/photos` | 사진 업로드와 증거 검수 | S4, S5 |
| POST | `/api/reports/{id}/rehearsals` | 불법주정차 사전 점검 | S6 |
| GET | `/api/reports/{id}/guide` | 단계별 접수 안내 | S7, S8 |
| POST | `/api/reports/{id}/drafts` | 신고 문구 대필 | S7 |
| GET | `/api/reports/{id}/case-preview` | 사례 공유 미리보기 | S14 |
| POST | `/api/reports/{id}/case` | 사례로 공유 | S14 |
| DELETE | `/api/reports/{id}/case` | 공유 내리기 | S11 |
| GET | `/api/cases` | 사례 목록 | S12 |
| GET | `/api/cases/{id}` | 사례 상세 | S13 |
| PUT | `/api/cases/{id}/like` | 도움돼요 누르기 | S13 |
| DELETE | `/api/cases/{id}/like` | 도움돼요 취소 | S13 |
| GET | `/api/procedures/{type_id}` | 신고 절차 데이터 조회 | S4, S7 |
| GET | `/api/health` | 서버 상태 확인 | - |

---

## 3. 상황 분석

### POST `/api/analyses`

사용자가 올린 사진과 글을 분석해 신고 가능한 항목을 돌려줍니다. S1에서 "보내기"를 누르면 호출합니다.

**요청** (`multipart/form-data`)

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `text` | string | 조건부 | 상황 설명. 최대 500자 |
| `photos` | file[] | 조건부 | 현장 사진. 최대 4장 |
| `address` | string | 아니요 | 사용자가 알려 준 위치. 없으면 AI가 사진과 글에서 추정합니다 |

`text`와 `photos` 중 하나는 반드시 있어야 합니다.

**응답** `201`

```json
{
  "id": "0c7f...",
  "created_at": "2026-11-14T14:02:00+09:00",
  "input": {
    "text": "인도에 차가 올라와 있어요",
    "photos": [{ "id": "a1b2...", "url": "/uploads/a1b2....jpg" }]
  },
  "reportable": true,
  "summary": "인도 위에 주차된 차량 1대와, 전봇대 아래 무단투기된 쓰레기가 보여요. 아래 2건을 신고할 수 있습니다.",
  "items": [
    {
      "type_id": "illegal_parking",
      "category": "report",
      "label": "불법주정차 (인도)",
      "subtitle": "과태료 부과 대상 · 안전신문고",
      "reason": "인도는 6대 주정차 금지구역이라 주민 신고만으로 과태료가 부과됩니다.",
      "detail": { "zone": "sidewalk" }
    },
    {
      "type_id": "trash_dumping",
      "category": "complaint",
      "label": "쓰레기 무단투기",
      "subtitle": "구청 청소과 처리 · 안전신문고",
      "reason": "공공장소에 종량제 봉투 없이 버려진 생활쓰레기는 무단투기 신고 대상입니다.",
      "detail": {}
    }
  ],
  "unsupported_items": [
    { "label": "전봇대 낙서", "message": "아직 안내하지 못하는 유형이에요" }
  ],
  "not_reportable": null,
  "location": { "address": "서울시 마포구 ○○로 12", "district": "마포구", "dong": "서교동" },
  "emergency": false,
  "disclaimer": "참고용 안내이며 최종 판단은 담당 기관이 합니다."
}
```

| 필드 | 설명 |
|---|---|
| `reportable` | 신고 가능한 항목이 하나라도 있으면 `true` |
| `items[].subtitle` | 체크박스 아래 한 줄. 절차 데이터의 `agency`, `channel.name`으로 서버가 조립합니다 |
| `items[].reason` | "왜 신고가 되나요?"를 펼쳤을 때 보이는 근거 |
| `items[].detail.zone` | 불법주정차만. `fire_hydrant`, `intersection_corner`, `bus_stop`, `crosswalk`, `school_zone`, `sidewalk` 중 하나 |
| `unsupported_items` | 보이지만 4개 유형에 속하지 않는 문제 |
| `location` | 추정하지 못하면 각 값이 `null` |
| `emergency` | 사람이 다쳤거나 위험이 진행 중으로 보이면 `true`. 프론트가 112·119 안내를 띄웁니다 |

**신고 불가일 때** (S3 시나리오 B) `reportable`이 `false`이고 `items`가 빈 배열입니다.

```json
{
  "reportable": false,
  "items": [],
  "not_reportable": {
    "title": "신고가 어려운 상황이에요",
    "message": "아파트 단지 안 주차장은 사유지라 주민신고 대상이 아니에요. 관리사무소에 문의해 보세요.",
    "basis": "주민신고는 도로 위 6대 금지구역(소화전, 교차로 모퉁이, 버스정류소, 횡단보도, 어린이보호구역, 인도)에만 적용돼요."
  }
}
```

`items`의 `type_id`와 접수처는 `backend/data/*.json`에 있는 값만 쓸 수 있습니다. AI가 목록에 없는 유형을 돌려주면 서버가 `unsupported_items`로 옮깁니다.

### GET `/api/analyses/{id}`

`POST /api/analyses`와 같은 본문을 돌려줍니다. 새로고침이나 "이어서 하기"에 씁니다.

### POST `/api/analyses/{id}/reports`

S3에서 체크한 항목으로 신고 건을 만듭니다. 선택한 순서가 진행 순서(`sequence`)가 됩니다.

**요청**

```json
{ "type_ids": ["trash_dumping", "illegal_parking"] }
```

**응답** `201`

```json
{
  "analysis_id": "0c7f...",
  "total": 2,
  "reports": [
    { "id": "r1...", "type_id": "trash_dumping", "sequence": 1, "status": "preparing" },
    { "id": "r2...", "type_id": "illegal_parking", "sequence": 2, "status": "preparing" }
  ]
}
```

- 분석 결과의 `items`에 없는 `type_id`를 보내면 `422`입니다.
- 서버는 이때 분석에 쓴 사진을 각 신고 건의 증거 장면과 대조합니다. 이미 충족된 장면은 S4에서 완료로 표시됩니다. 이 대조는 분석 때 받은 AI 결과를 재사용하며 AI를 다시 호출하지 않습니다.

---

## 4. 신고 건

### 신고 건 객체

`GET /api/reports/{id}`와 `PATCH`의 응답 형태입니다.

```json
{
  "id": "r1...",
  "analysis_id": "0c7f...",
  "sequence": 1,
  "total": 2,
  "type_id": "trash_dumping",
  "category": "complaint",
  "label": "쓰레기 무단투기",
  "status": "resolved",
  "status_label": "처리 완료 · 수용",
  "location": { "address": "서울시 마포구 ○○로 12", "district": "마포구", "dong": "서교동" },
  "created_at": "2026-11-14T14:02:00+09:00",
  "evidence_progress": { "done": 2, "required": 2 },
  "current_step": 7,
  "step_count": 7,
  "channel": { "name": "안전신문고", "menu_path": ["생활불편 신고", "쓰레기·폐기물"] },
  "photos": [
    { "id": "a1b2...", "url": "/uploads/a1b2....jpg", "scene_id": "overview" }
  ],
  "draft_text": "서울시 마포구 ○○로 12 앞 전봇대 아래에 ...",
  "receipt_number": null,
  "filed_at": "2026-11-14T14:20:00+09:00",
  "result": "accepted",
  "result_reason": null,
  "resolved_at": "2026-11-16T10:00:00+09:00",
  "timeline": [
    { "key": "input", "label": "상황 입력", "note": "11월 14일 오후 2:02", "done": true },
    { "key": "evidence", "label": "증거 준비", "note": "사진 2장 확인", "done": true },
    { "key": "filed", "label": "접수 완료", "note": "안전신문고 > 생활불편", "done": true },
    { "key": "result", "label": "처리 결과", "note": "수용", "done": true }
  ],
  "case_id": null,
  "next_report_id": "r2..."
}
```

| 필드 | 설명 |
|---|---|
| `sequence`, `total` | 화면 오른쪽 위 "1/2건" 표시 |
| `status_label` | 목록 배지 문구. 서버가 조립합니다 (`접수 완료`, `처리 완료 · 수용`, `준비 중 · 증거 1/3`) |
| `current_step` | 접수 안내에서 마지막으로 끝낸 단계 번호. 시작 전이면 `0` |
| `receipt_number` | 입력하지 않았으면 `null`. S9에서는 "접수번호 입력 안 함"으로 표시 |
| `case_id` | 사례로 공유했으면 사례 ID |
| `next_report_id` | 같은 분석에서 아직 접수하지 않은 다음 건. 없으면 `null` |

### GET `/api/reports`

내 신고 목록입니다. 요청한 기기의 건만 돌려줍니다.

**쿼리**

| 이름 | 값 | 설명 |
|---|---|---|
| `status` | `preparing`, `filed`, `resolved` | 생략하면 전체 (S10 필터 칩) |
| `limit` | 1~50, 기본 20 | S1의 "이어서 하기" 카드는 `status=preparing&limit=1` |
| `cursor` | string | 다음 페이지 |

**응답** `200`

```json
{
  "items": [
    {
      "id": "r3...",
      "type_id": "illegal_ad",
      "category": "complaint",
      "label": "불법 광고물",
      "status": "preparing",
      "status_label": "준비 중 · 증거 1/3",
      "district": "마포구",
      "dong": "합정동",
      "created_at": "2026-11-12T09:30:00+09:00",
      "thumbnail_url": "/uploads/c3d4....jpg",
      "resumable": true
    }
  ],
  "next_cursor": null
}
```

최신순으로 정렬합니다. `resumable`이 `true`이면 "이어서 하기"를 보여 줍니다.

### GET `/api/reports/{id}`

위의 신고 건 객체를 돌려줍니다.

### PATCH `/api/reports/{id}`

보낸 필드만 수정합니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `current_step` | int | 접수 안내에서 "했어요"를 누를 때마다 보냅니다 |
| `status` | `filed` | 마지막 단계 "접수 완료"를 누를 때. 서버가 `filed_at`을 기록합니다 |
| `receipt_number` | string \| null | 접수번호. 선택 입력 |
| `result` | `accepted`, `rejected`, `unknown` | S11에서 사용자가 고른 처리 결과. `accepted`나 `rejected`면 `status`가 `resolved`로 바뀝니다 |
| `result_reason` | string \| null | 불수용 사유. 최대 300자 |

- `status`는 `preparing → filed → resolved` 순서로만 바뀝니다. 거꾸로 보내면 `409`입니다.
- 필수 증거 장면이 모두 `sufficient`가 아니면 `filed`로 바꿀 수 없습니다(`409`).

**응답** `200`: 신고 건 객체

---

## 5. 증거

### GET `/api/reports/{id}/evidence`

S4의 증거 체크리스트입니다.

**응답** `200`

```json
{
  "report_id": "r1...",
  "label": "쓰레기 무단투기",
  "intro": "쓰레기 무단투기부터 준비할게요. 사진이 1장 더 필요해요.",
  "required_count": 2,
  "done_count": 1,
  "complete": false,
  "capture_in_app": true,
  "scenes": [
    {
      "scene_id": "overview",
      "label": "쓰레기 전체가 보이는 사진",
      "required": true,
      "photo": { "id": "a1b2...", "url": "/uploads/a1b2....jpg" },
      "review": { "status": "sufficient", "message": "올리신 사진으로 충분해요" }
    },
    {
      "scene_id": "location",
      "label": "주변 건물이나 도로명이 보이는 사진",
      "required": true,
      "photo": null,
      "review": null
    }
  ]
}
```

| 필드 | 설명 |
|---|---|
| `capture_in_app` | `true`면 이 앱에서 찍어 검수합니다. 불법주정차는 `false`이며, 대신 사전 점검(`/rehearsals`)을 씁니다 |
| `scenes[].photo` | 아직 사진이 없으면 `null`. 프론트는 "촬영하기" 버튼을 보여 줍니다 |
| `complete` | 필수 장면이 모두 `sufficient`면 `true`. 접수 안내로 넘어갈 수 있습니다 |

### POST `/api/reports/{id}/photos`

사진을 올리고, `scene_id`가 있으면 그 장면의 증거로 충분한지 검수합니다.

**요청** (`multipart/form-data`)

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `photo` | file | 예 | 사진 1장 |
| `scene_id` | string | 아니요 | 검수할 장면. 절차 데이터의 `evidence_scenes[].scene_id` |

**응답** `201`

```json
{
  "photo": { "id": "e5f6...", "url": "/uploads/e5f6....jpg", "scene_id": "location" },
  "review": {
    "status": "insufficient",
    "message": "도로명 표지판이 잘려서 위치를 알기 어려워요.",
    "retake_tip": "두세 걸음 뒤로 물러나서 건물 간판이 함께 나오게 다시 찍어 주세요."
  },
  "evidence": { "required_count": 2, "done_count": 1, "complete": false }
}
```

| `review.status` | `message` | `retake_tip` |
|---|---|---|
| `sufficient` | 왜 충분한지 한 줄 | `null` |
| `insufficient` | 무엇이 부족한지 | 어떻게 다시 찍을지. 반드시 채웁니다 |
| `undetermined` | 판단하지 못한 이유 (어두움, 흐림 등) | 다시 찍는 방법. 반드시 채웁니다 |

- 같은 장면에 다시 올리면 이전 사진을 대체합니다.
- `scene_id` 없이 올리면 검수하지 않고 `review`가 `null`입니다.

### POST `/api/reports/{id}/rehearsals`

불법주정차 사전 점검입니다(S6). 올린 사진으로 요건을 미리 확인하고, 안전신문고 앱에서 찍을 방법을 안내합니다. `type_id`가 `illegal_parking`이 아닌 건에 호출하면 `409`입니다.

**요청**

```json
{ "photo_id": "a1b2..." }
```

`photo_id`를 생략하면 분석 때 올린 첫 사진을 씁니다.

**응답** `200`

```json
{
  "passed": false,
  "zone": "sidewalk",
  "checks": [
    { "key": "zone", "status": "sufficient", "label": "금지구역: 인도 위 주차", "detail": null },
    { "key": "plate_readable", "status": "sufficient", "label": "번호판이 식별돼요", "detail": null },
    {
      "key": "background_included",
      "status": "insufficient",
      "label": "주변 배경이 부족해요",
      "detail": "차량만 크게 찍혔어요. 인도 경계석과 옆 건물이 함께 보이게 찍어야 합니다."
    }
  ],
  "capture_guide": {
    "title": "안전신문고 앱에서 이렇게 찍으세요",
    "steps": [
      "차량 뒤쪽에서 번호판과 인도 경계석이 함께 나오게 1장",
      "그 자리에서 움직이지 말고 1분 기다리기",
      "같은 위치, 같은 방향으로 1장 더"
    ],
    "warning": "앞에서 1장, 옆에서 1장은 반려돼요.",
    "interval_seconds": 60,
    "interval_note": "어린이보호구역은 5분 간격이 필요할 수 있어요"
  }
}
```

- `passed`는 세 항목이 모두 `sufficient`일 때 `true`입니다. `false`여도 `capture_guide`는 항상 돌려줍니다. 본촬영에서 고치면 되기 때문입니다.
- `zone`이 금지구역이 아니면 `checks[0].status`가 `insufficient`이고, 프론트는 접수 안내로 넘어가지 않습니다.
- `interval_seconds`는 절차 데이터의 구역별 값입니다. 타이머(S6-3)는 프론트가 이 값으로 돌립니다.
- 본촬영 사진은 이 서버에 올리지 않습니다. 사전 점검을 본 것만으로 증거 단계를 완료 처리합니다.

---

## 6. 접수 안내

### GET `/api/reports/{id}/guide`

단계별 접수 안내입니다(S7). 같은 분석의 앞 건에서 이미 끝낸 단계는 `skipped`로 표시합니다(S8).

**응답** `200`

```json
{
  "report_id": "r2...",
  "label": "불법주정차 (인도)",
  "sequence": 2,
  "total": 2,
  "channel": {
    "name": "안전신문고",
    "web_url": "https://www.safetyreport.go.kr",
    "menu_path": ["불법 주정차 신고", "인도"]
  },
  "current_step": 0,
  "carry_over": [
    { "label": "안전신문고 로그인", "message": "이미 하셨어요, 건너뜁니다" },
    { "label": "위치 확인", "message": "같은 장소라 그대로 씁니다" },
    { "label": "사진", "message": "안전신문고 앱에서 새로 찍어야 해요" }
  ],
  "steps": [
    {
      "order": 1,
      "step_id": "open_site",
      "title": "안전신문고에 접속하세요",
      "body": "safetyreport.go.kr 또는 안전신문고 앱을 엽니다.",
      "action": { "kind": "open_link", "button_label": "안전신문고 열기", "url": "https://www.safetyreport.go.kr" },
      "skipped": true,
      "verified": false
    },
    {
      "order": 4,
      "step_id": "attach_photos",
      "title": "사진 항목에 아래 2장을 첨부하세요",
      "body": null,
      "action": {
        "kind": "save_photos",
        "button_label": "사진 저장",
        "photos": [{ "id": "a1b2...", "url": "/uploads/a1b2....jpg" }]
      },
      "skipped": false,
      "verified": false
    },
    {
      "order": 6,
      "step_id": "fill_content",
      "title": "내용 항목에 아래 글을 붙여 넣으세요",
      "body": null,
      "action": { "kind": "copy_text", "button_label": "글 복사", "text": null },
      "skipped": false,
      "verified": false
    }
  ]
}
```

| `action.kind` | 버튼 동작 | 추가 필드 |
|---|---|---|
| `open_link` | 새 탭으로 열기 | `url` |
| `confirm` | "했어요" | 없음 |
| `save_photos` | 사진 저장 | `photos` |
| `copy_text` | 글 복사 | `text`. `null`이면 프론트가 `/drafts`를 호출해 채웁니다 |
| `submit` | "접수 완료" | 없음. 누르면 `PATCH`로 `status: "filed"` |

- `carry_over`는 `sequence`가 2 이상일 때만 채워지고, 첫 건에서는 빈 배열입니다.
- `verified`가 `false`인 단계는 안전신문고 실제 화면과 대조하지 못한 내용입니다. 프론트는 "실제 화면과 다를 수 있어요"를 작게 표시합니다.
- 단계의 제목과 메뉴 경로는 절차 데이터에서 그대로 가져옵니다. AI가 만들지 않습니다.

### POST `/api/reports/{id}/drafts`

신고 내용 문구를 대신 씁니다(S7 6단계). 만든 문구는 신고 건의 `draft_text`에 저장됩니다.

**요청**

```json
{ "tone": "default" }
```

| `tone` | 설명 |
|---|---|
| `default` | 기본. 첫 호출 |
| `shorter` | "더 짧게" |
| `politer` | "더 정중하게" |

**응답** `200`

```json
{
  "text": "서울시 마포구 ○○로 12 앞 전봇대 아래에 종량제 봉투를 쓰지 않은 생활쓰레기가 무단투기되어 있습니다. 2026년 11월 14일 오후 2시경 확인했으며, 악취와 통행 불편이 있어 수거와 단속을 요청드립니다.",
  "tone": "default"
}
```

문구에는 위치, 확인한 일시, 상황, 요청 사항이 들어갑니다. 위치를 모르면 `[위치를 적어 주세요]` 자리표시를 넣습니다.

---

## 7. 사례 공유

### GET `/api/reports/{id}/case-preview`

공유하기 전 미리보기입니다(S14). 저장하지 않습니다. `status`가 `preparing`인 건은 `409`입니다.

**응답** `200`

```json
{
  "title": "전봇대 아래 쓰레기, 사진 2장으로 수거까지",
  "type_id": "trash_dumping",
  "result_label": "수용",
  "district": "마포구",
  "period": "2026년 11월",
  "sections": [
    { "heading": "어떤 상황이었나", "body": "..." },
    { "heading": "어떤 사진을 준비했나", "body": "..." },
    { "heading": "어디에 어떻게 접수했나", "body": "..." },
    { "heading": "결과와 걸린 시간", "body": "..." },
    { "heading": "다음 사람을 위한 팁", "body": "..." }
  ],
  "photos": [{ "id": "a1b2...", "url": "/uploads/a1b2....jpg" }],
  "removed": [
    { "label": "상세 주소", "treatment": "구 단위까지만 표시" },
    { "label": "날짜와 시각", "treatment": "월 단위까지만 표시" },
    { "label": "접수번호", "treatment": "삭제" }
  ],
  "photo_notice": "사진은 가리지 않고 그대로 공개돼요."
}
```

### POST `/api/reports/{id}/case`

사례로 공유합니다.

**요청**

```json
{ "consent": true }
```

`consent`가 `true`가 아니면 `422`입니다. 이미 공유한 건이면 `409`입니다.

**응답** `201`: 사례 상세 객체 (8장)

### DELETE `/api/reports/{id}/case`

공유를 내립니다. 사례 글과 도움돼요 기록을 지웁니다. 사진 원본과 신고 건은 남습니다.

**응답** `204`

---

## 8. 사례

로그인이 없으므로 사례 조회는 누구나 할 수 있습니다. `X-Device-Id`는 "내가 도움돼요를 눌렀는지" 표시에만 씁니다.

### GET `/api/cases`

**쿼리**

| 이름 | 값 | 설명 |
|---|---|---|
| `type` | `type_id` 중 하나 | 생략하면 전체 (S12 필터 칩) |
| `limit` | 1~50, 기본 20 | |
| `cursor` | string | 다음 페이지 |

**응답** `200`

```json
{
  "items": [
    {
      "id": "k1...",
      "title": "처음엔 반려됐어요. 옆모습 사진이 문제였습니다",
      "type_id": "illegal_parking",
      "type_label": "불법주정차",
      "result_label": "불수용 → 재신고 수용",
      "district": "성동구",
      "like_count": 41,
      "cover_url": "/uploads/f7g8....jpg"
    }
  ],
  "next_cursor": null
}
```

최신순으로 정렬합니다.

### GET `/api/cases/{id}`

**응답** `200`

```json
{
  "id": "k1...",
  "title": "처음엔 반려됐어요. 옆모습 사진이 문제였습니다",
  "type_id": "illegal_parking",
  "type_label": "불법주정차",
  "result_label": "불수용 → 재신고 수용",
  "district": "성동구",
  "period": "2026년 9월",
  "sections": [
    { "heading": "어떤 상황이었나", "body": "인도 위에 차가 올라와 있어서 보행자가 차도로 내려가야 했어요.", "photos": [] },
    {
      "heading": "어떤 사진을 준비했나",
      "body": "처음에는 앞에서 1장, 옆에서 1장을 찍었어요. 두 번째에는 뒤쪽 같은 자리에서 1분 간격으로 2장을 찍었어요.",
      "photos": [{ "id": "f7g8...", "url": "/uploads/f7g8....jpg" }]
    }
  ],
  "like_count": 41,
  "liked_by_me": false,
  "is_mine": false,
  "created_at": "2026-09-20T10:00:00+09:00"
}
```

- `period`는 월 단위까지만 내려갑니다. `created_at`은 사례를 공유한 시각이며 신고 일시가 아닙니다.
- "나도 비슷한 상황이에요" 버튼은 프론트가 `type_id`를 들고 S1으로 이동합니다. API 호출은 없습니다.

### PUT `/api/cases/{id}/like`, DELETE `/api/cases/{id}/like`

기기당 한 번만 누를 수 있습니다. 여러 번 호출해도 결과가 같습니다.

**응답** `200`

```json
{ "like_count": 42, "liked_by_me": true }
```

---

## 9. 기타

### GET `/api/procedures/{type_id}`

`backend/data/{type_id}.json`의 내용을 그대로 돌려줍니다. 스키마는 `.kiro/steering/structure.md`를 따릅니다. 없는 `type_id`는 `404`입니다.

### GET `/api/health`

```json
{ "status": "ok" }
```

### 사진 파일

- 사진은 S3 비공개 버킷에 저장합니다. DB에는 S3 키만 둡니다.
- API 응답의 사진 `url`은 요청 시점에 만든 presigned GET URL입니다. 1시간 뒤 만료되므로 프론트는 이 주소를 저장해 두지 않고, 필요할 때 API를 다시 호출합니다.
- 이 문서의 예시에 나오는 `/uploads/....jpg`는 자리표시입니다. 실제 값은 `https://<버킷>.s3.ap-northeast-2.amazonaws.com/...?X-Amz-...` 형태입니다.
- 내 신고의 사진은 `X-Device-Id`가 맞는 요청에만 `url`을 내려 줍니다. 공유하지 않은 사진은 다른 기기가 주소를 받을 수 없습니다.
- 사례로 공유한 사진은 누구에게나 `url`을 내려 주며, 원본 그대로 공개됩니다.
- `S3_BUCKET`이 없는 로컬 개발 환경에서는 백엔드가 디스크에 저장하고 자체 경로를 `url`로 돌려줍니다.

### 배포 환경에서의 제약

- HTTPS는 CloudFront가 받고, 오리진은 EC2의 FastAPI입니다.
- CloudFront의 오리진 응답 제한 시간은 60초입니다. AI를 호출하는 엔드포인트는 50초 안에 응답해야 하며, 넘으면 `502 ai_unavailable`을 돌려줍니다.
- `/api/*`는 캐시하지 않습니다.

---

## 10. 목업과 다르게 정한 부분

| 목업 | 이 명세 | 이유 |
|---|---|---|
| S13에 "가려진 사진"이 표시됨 | 사진을 원본 그대로 돌려줌 | 번호판·얼굴 가리기는 후순위로 결정 |
| S14에 "차량 번호판, 사람 얼굴", "전단지 속 전화번호·상호"를 지운다고 표시됨 | `removed` 목록에서 빼고 `photo_notice`로 원본 공개를 알림 | 위와 같음. 실제로 지우지 않는 항목을 지운다고 표시하면 안 됨 |
| S6 타이머가 약 6초 | `interval_seconds`는 60 | 목업은 시연용으로 빠르게 돌린 값 |
| S1 예시 칩 4개 | API 없음 | 프론트에 고정 문구로 둠 |

## 11. 정해야 할 것

- **위치 입력**: 목업에는 주소를 입력하는 화면이 없습니다. 지금은 AI가 사진과 글에서 추정하고, 못 하면 `null`입니다. 브라우저 위치 권한을 받아 좌표를 보낼지 정해야 합니다. 좌표를 받으면 주소로 바꾸는 외부 API가 필요합니다.
- **S14 화면 수정**: 위 표의 차이를 목업에도 반영할지 정해야 합니다.
- **불법주정차 접수 확인**: 본촬영 사진을 서버가 받지 않으므로, 사용자가 실제로 접수했는지는 "접수 완료" 버튼으로만 압니다.
