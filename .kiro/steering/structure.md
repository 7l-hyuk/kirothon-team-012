---
inclusion: always
---

# 레포 구조와 이름 규칙

아래는 **초안**입니다. 구현하면서 달라지면 이 문서를 같이 고칩니다.

## 최상위
```
.
├── README.md
├── BUILD_REPORT.md
├── SUBMISSION_GUIDE.md
├── PRESENTATION.pdf          # 제출 때 추가
├── Dockerfile                # 멀티 스테이지: 프론트 빌드 → 백엔드 이미지
├── docker-compose.yml        # app + db (PostgreSQL, 이름 있는 볼륨)
├── deploy/                   # 배포 절차 문서와 스크립트 (EC2, CloudFront, S3, IAM)
├── docs/
│   └── api-spec.md           # 백엔드 API 명세 (API의 기준 문서)
├── .kiro/
│   ├── steering/             # product.md, tech.md, structure.md
│   ├── specs/
│   └── hooks/
├── backend/
└── frontend/
```

## backend/
```
backend/
├── pyproject.toml            # uv 관리
├── .env                      # 커밋 금지
├── app/
│   ├── main.py               # FastAPI `app`, 라우터 등록, 정적 파일 서빙, 시작 시 DB 생성(lifespan). seed는 사례 구현 때
│   ├── config.py             # 환경변수 읽기
│   ├── db.py                 # SQLModel 엔진, 시작 시 테이블 생성·재시도, DB 준비 확인
│   ├── deps.py               # X-Device-Id 추출, 요청 단위 DB 세션(SessionDep)
│   ├── timeutil.py           # KST, now_kst(), today_kst()
│   ├── errors.py             # 오류 코드와 처리기
│   ├── models/               # SQLModel 테이블(tables.py), 시각 타입(types.py)
│   ├── schemas/              # API 요청·응답, AI 구조화 출력용 Pydantic 모델
│   ├── routers/              # API 라우터 (기능별 파일)
│   ├── ai/                   # Anthropic SDK 호출은 여기에서만
│   │   ├── client.py
│   │   ├── prompts/          # 프롬프트 템플릿
│   │   └── *.py              # analyze, review, rehearsal, draft 등 기능별
│   ├── services/             # store.py(DB 저장소), quota.py(AI 호출 상한), photos.py(업로드 검사·축소), 절차 데이터 로딩 등
│   ├── storage/              # 사진 저장소. base.py(인터페이스) + s3.py + local.py, get_storage()
│   └── seed.py               # 사례 예시 3~4건 (사례 구현 때 추가)
├── data/
│   └── *.json                # 신고 절차 데이터 (사람이 검증한 값)
├── uploads/                  # 개발용 로컬 디스크 사진(`S3_BUCKET` 없을 때만). 커밋 금지
└── tests/
```

### 역할 요약
| 폴더 | 역할 |
|---|---|
| `routers/` | HTTP 경계. 검증과 응답 변환만 하고 로직은 `services/`, `ai/`로 넘김 |
| `ai/` | 프롬프트 구성, `messages.parse()` 호출, `stop_reason` 확인, 오류 변환 |
| `services/` | AI와 무관한 도메인 로직 |
| `storage/` | 사진 저장·조회. 인터페이스 뒤에 S3(boto3, presigned GET URL 생성)와 로컬 디스크 구현을 둠. `S3_BUCKET` 유무로 선택. 라우터·서비스는 구현을 직접 부르지 않음 |
| `schemas/` | 외부에 보이는 데이터 모양. DB 모델과 분리 |
| `data/` | 절차의 단일 출처(source of truth). 코드는 값을 하드코딩하지 않음 |

## frontend/
```
frontend/
├── package.json
├── vite.config.ts            # /api → http://localhost:8000 프록시
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx               # 라우팅, 하단 탭 3개
    ├── pages/                # 화면 단위 (S1, S10, S12 등 탭 진입 화면)
    ├── components/
    │   ├── cards/            # 항목 선택, 증거, 단계 안내 카드 (대화 안에 끼워지는 것)
    │   ├── chat/             # 말풍선, 진행 표시줄
    │   └── ui/               # 배지, 버튼, 상태 표시 등 공통
    ├── api/                  # fetch 래퍼. X-Device-Id 헤더를 여기서 붙임
    ├── hooks/                # useDeviceId, useTimer 등
    ├── types/                # 백엔드 스키마와 맞춘 타입
    └── lib/
```

## 이름 규칙
| 대상 | 규칙 | 예 |
|---|---|---|
| Python 파일·함수·변수 | snake_case | `report_steps.py` |
| Python 클래스 | PascalCase | `AnalysisResult` |
| React 컴포넌트 파일 | PascalCase.tsx | `ItemSelectCard.tsx` |
| 훅 | `use` + camelCase | `useDeviceId.ts` |
| 그 외 TS 파일 | camelCase.ts | `client.ts` |
| JSON 데이터 파일 | 영문 소문자, 유형 id와 같은 이름 | `illegal_parking.json` |
| DB 테이블·컬럼 | snake_case, 테이블은 복수형 | `reports`, `device_id` |
| 유형 id (`type_id`) | `illegal_parking`, `trash_dumping`, `illegal_ad`, `facility_damage` | |
| 사용자에게 보이는 문구 | 한국어 해요체. 코드 식별자는 영어 | |

화면 코드와 문서의 화면 번호(S1~S14)는 컴포넌트 주석이나 파일 상단 주석에 적어 둡니다.

## API 경로 규칙
- 모두 `/api` 아래, 소문자 kebab-case, 복수형 명사. 동사는 HTTP 메서드로 표현합니다.
- 모든 요청에 `X-Device-Id` 헤더. 오류는 `{ "detail": "해요체 문구", "code": "snake_case 오류 코드" }` 형태. `code` 목록은 명세를 따릅니다.

요청·응답의 상세는 `docs/api-spec.md`가 기준이며, 이 표와 다르면 명세가 우선합니다. API를 바꿀 때는 명세를 먼저 고칩니다.

#[[file:docs/api-spec.md]]

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

## 신고 절차 JSON 스키마 (초안)
파일 하나가 유형 하나입니다. 값은 사람이 검증한 것만 넣고, 확인되지 않은 값은 `verified: false`로 표시합니다.

```json
{
  "type_id": "trash_dumping",
  "label": "쓰레기 무단투기",
  "category": "complaint",
  "agency": "구청 청소과",
  "channel": {
    "name": "안전신문고",
    "web_url": "https://www.safetyreport.go.kr",
    "menu_path": ["생활불편 신고", "쓰레기·폐기물"]
  },
  "eligibility": {
    "reportable_when": ["공공장소에 무단투기된 생활쓰레기"],
    "not_reportable_when": [
      { "reason": "사유지라 주민신고 대상이 아니에요", "advice": "관리사무소에 문의해 보세요" }
    ]
  },
  "evidence_scenes": [
    {
      "scene_id": "overview",
      "label": "쓰레기 전체가 보이는 사진",
      "required": true,
      "pass_criteria": "쓰레기 더미 전체가 프레임 안에 있다",
      "retake_tip": "쓰레기가 잘리지 않게 한두 걸음 물러나 주세요"
    }
  ],
  "capture_rules": {
    "photo_count_min": 2,
    "interval_seconds": null,
    "same_position_required": false
  },
  "steps": [
    {
      "step_id": "open_site",
      "order": 1,
      "title": "안전신문고에 접속하세요",
      "action": { "kind": "open_link", "button_label": "안전신문고 열기" },
      "reusable": true,
      "verified": false
    }
  ],
  "input_fields": [
    { "field_id": "content", "label": "내용", "kind": "draft_text" }
  ],
  "verified": false,
  "source_note": "확인한 날짜, 확인 방법, 출처"
}
```

- `action.kind`: `open_link` / `confirm` / `save_photos` / `copy_text` / `submit` 중 하나.
- `reusable`: 여러 건을 이어서 신고할 때 건너뛸 수 있는 단계(로그인, 위치)면 `true`.
- 불법주정차 파일(`illegal_parking.json`)은 추가로 다음을 둡니다.
  - `zones`: 6대 금지구역 목록과 구역별 `interval_seconds`(기본 60, 어린이보호구역 등은 300 `[확인 필요]`).
  - `rehearsal_checks`: `zone`, `plate_readable`, `background_included`.
  - `capture_rules.same_position_required: true`, `capture_rules.photo_count_min: 2`.
- 서버 시작 때 JSON을 Pydantic 모델로 읽어 검증하고, 형식이 틀리면 시작을 실패시킵니다.

## DB 테이블 (SQLModel)
`analyses`, `reports`, `photos`, `ai_usage`는 구현했고(`backend/app/models/tables.py`), 나머지는 아직 초안입니다. ID는 UUID 문자열(`VARCHAR(36)`)입니다.

| 테이블 | 주요 컬럼 |
|---|---|
| `analyses` | `id`, `device_id`, `situation_text`, `result`(AI 분석 결과 JSON. 사진 URL이 든 `input`은 제외), `address`(null 가능), `district`(null 가능), `dong`(null 가능), `created_at`, `scene_matches`(JSON), `item_photo_ids`(JSON) |
| `reports` | `id`, `device_id`, `analysis_id`, `type_id`, `category`, `label`, `sequence`, `total`, `status`(`preparing`/`filed`/`resolved`), `current_step`, `situation_text`, `location_text`, `district`, `dong`, `summary`, `zone`, `draft_text`, `receipt_number`, `result`(`accepted`/`rejected`/`unknown`/null), `result_reason`, `scenes`(JSON: 장면별 사진·검수 상태), `filed_at`, `resolved_at`, `created_at`, `updated_at`. `(analysis_id, sequence)` 유일 |
| `photos` | `id`, `device_id`, `analysis_id`(null 가능), `report_id`(null 가능), `s3_key`(가짜 모드 자리표시 사진은 null), `scene_id`(null 가능), `review_status`(`sufficient`/`insufficient`/`undetermined`/null), `review_message`, `retake_tip`, `taken_order`, `created_at` |
| `step_progress` | `id`, `report_id`, `step_id`, `done`, `done_at` (미구현. 진행 단계는 `reports.current_step`으로 충분해서 만들지 않았습니다) |
| `ai_usage` | `id`, `device_id`, `day`(KST 날짜), `count` (`device_id` + `day` 유일 제약) |
| `cases` | `id`, `report_id`(seed는 null), `type_id`, `title`, `body`, `result`, `district`(구 단위), `month`(예: 2026-11), `like_count`, `is_published`, `created_at` |
| `case_likes` | `id`, `case_id`, `device_id` (`case_id` + `device_id` 유일 제약) |
| `case_photos` | `id`, `case_id`, `s3_key` |

- `status` 값은 화면의 준비 중 / 접수 완료 / 처리 완료에 대응합니다.
- 사진 테이블에는 URL을 저장하지 않습니다. 응답을 만들 때 `s3_key`로 presigned URL을 만듭니다. 로컬 디스크 구현에서는 `s3_key` 자리에 저장소 내부 키(`photos/{yyyy}/{mm}/{photo_id}.jpg`, `UPLOAD_DIR` 기준 상대 경로)를 넣고 URL은 `GET /api/photos/{photo_id}/file`입니다.
- `cases`에는 상세 주소, 정확한 날짜, 접수번호 컬럼을 두지 않습니다. 비식별화는 저장 시점에 끝냅니다.
- 사례 seed(3~4건)는 `app/seed.py`에서 넣고, 이미 있으면 다시 넣지 않습니다.
