# 설계: 사례 공유

## 구조

```
backend/app/
├── models/tables.py        # + Case, CaseLike, CasePhoto, CaseDraft (새 테이블만)
├── schemas/cases.py        # API 응답·요청, CaseFacts(AI에 넘기는 자료)
├── schemas/ai_outputs.py   # + CaseDraftOutput
├── ai/case.py              # 사례 글 호출 (parse_message)
├── ai/prompts.py           # + case_system, case_user_text
├── services/cases.py       # 미리보기, 공유, 내리기, 목록, 좋아요, 비식별화
├── routers/cases.py        # 7개 경로 + 좋아요 2개
├── seed.py                 # 예시 사례 넣기
└── main.py                 # lifespan에서 seed, 라우터 등록
backend/data/seed_cases.json
```

`mock/service.report_out`이 `services.cases.case_id_for_report()`로 `case_id`를 채운다. `services/cases.py`는 `mock/service.py`를 import하지 않는다(순환 방지).

## 테이블 (새로 추가)

| 테이블 | 컬럼 |
|---|---|
| `cases` | `id`(UUID 문자열), `report_id`(FK `reports.id`, **유일**, 예시는 NULL), `device_id`(NULL 가능), `type_id`, `title`, `sections`(JSON: `[{heading, body}]` 5개), `result_label`, `district`(NULL 가능), `period`(예: "2026년 11월"), `like_count`, `is_seed`, `created_at` |
| `case_likes` | `id`, `case_id`(FK), `device_id`, `(case_id, device_id)` 유일 |
| `case_photos` | `id`, `case_id`(FK), `photo_id`(FK `photos.id`), `position` |
| `case_drafts` | `id`, `report_id`(FK, **유일**), `device_id`, `fingerprint`, `title`, `sections`(JSON), `result_label`, `district`, `period`, `created_at` |

- `case_photos`는 `s3_key`가 아니라 `photo_id`를 둔다. 사진 URL을 만드는 길(`store.photo_url`)이 하나로 유지되고, 로컬 디스크 URL이 사진 ID를 쓰기 때문이다.
- 신고 건의 `case_id`는 `reports`에 컬럼을 더하지 않고 `cases.report_id`로 조회한다.
- `cases`에는 상세 주소, 접수번호, 정확한 날짜 컬럼이 없다. 비식별화는 초안을 만들 때 끝난다.
- `case_drafts.fingerprint`는 `"{status}|{result}|{result_reason}"`이다. 값이 다르면 초안을 새로 만든다.

## 미리보기와 공유 흐름

```
GET case-preview
  신고 건 조회(기기 ID) → preparing이면 409
  → ensure_draft
       초안 있고 fingerprint 같음 → 그대로
       아니면 facts 조립 → (가짜 모드: 고정 형식 글 | 실제: 하루 상한 확인 → Claude) → 정리 → 저장
  → 응답(사진은 신고 건의 현재 사진)

POST case
  신고 건 조회 → consent 아니면 422 → preparing이면 409 → 이미 공유면 409
  → ensure_draft(저장된 초안 그대로) → cases + case_photos 한 트랜잭션 → 201
```

### facts (AI에 넘기는 자료)
유형, 구분(신고/민원), 금지구역, 분석 요약, 구(`district`), `period`, 사진 장수, 증거 장면과 검수 결과, 접수처와 메뉴 경로, 담당 기관, 촬영 규칙 한 줄(불법주정차), 진행 상태, 처리 결과, 불수용 사유, 접수부터 처리까지 걸린 일수.
상세 주소, 접수번호, 일이 든 날짜는 넣지 않는다. 문자열 자료(요약, 검수 문구, 사유)는 `scrub()`을 거친다.

### scrub (서버 쪽 비식별화)
AI에 넘기기 전과 AI가 돌려준 뒤에 같은 함수를 적용한다.
- 상세 주소(`location_text`)와 동(`dong`)은 구로 바꾼다(구가 없으면 "근처").
- 접수번호 문자열은 지운다.
- `N월 N일` → `N월`, `YYYY-MM-DD` → `YYYY-MM`, 오전·오후 시각, `HH:MM`은 지운다.
- 번호판 형태(`12가3456`)는 "번호판"으로, 전화번호 형태는 지운다.

### AI 출력 정리
- `CaseDraftOutput`은 `title`과 절 5개(`situation`, `photos`, `filing`, `result`, `tip`)다. 절 제목은 서버가 고정한다.
- 빈 필드는 고정 형식 글의 같은 필드로 채운다.
- 처리 결과가 없으면 `result` 절은 모델 출력과 상관없이 고정 형식 글로 바꾼다(결과를 지어내지 못하게).

### 고정 형식 글 (가짜 모드와 빈 필드 대체)
신고 건 자료와 절차 데이터(`backend/data/*.json`)의 값(증거 장면 이름, 통과 기준, 접수처, 메뉴, 촬영 규칙 경고)만 문장에 끼워 넣는다.

## 좋아요
- PUT: 기록이 없으면 `case_likes`에 넣고 같은 트랜잭션에서 `like_count + 1`(UPDATE). 유일 제약 위반은 이미 눌린 것으로 본다.
- DELETE: 지운 행이 1개일 때만 `like_count - 1`(0 아래로 내려가지 않게).
- 응답의 `like_count`는 DB에서 다시 읽는다.

## 목록
최신순(`created_at DESC, id`). `cursor`는 `GET /api/reports`와 같은 offset 문자열. `type`은 `TypeId`로 검증한다. `cover_url`은 페이지의 사례 ID로 `case_photos`를 한 번에 읽어 첫 사진을 쓴다.

## 예시 사례
- `app/seed.py`의 `seed_cases(session)`이 `cases`가 비었을 때만 `seed_cases.json`을 읽어 넣는다. ID는 `key`에서 만든 uuid5다.
- `main.lifespan`이 `init_db()`가 성공한 뒤 호출한다. 실패해도 앱은 뜬다.
- 제한: 시작할 때 DB가 없어 `init_db()`가 실패하면 그 프로세스에서는 예시를 넣지 않는다(다음 시작 때 넣는다).
- 예시 글은 형식(5개 절, 해요체)을 `app/seed.py`에서 검증한다.

## 오류
| 상황 | 응답 |
|---|---|
| 준비 중인 건의 미리보기·공유 | 409 `invalid_state` |
| 동의 없음 | 422 `validation_error` |
| 이미 공유 | 409 `invalid_state` |
| 다른 기기의 건, 공유하지 않은 건 내리기, 없는 사례 | 404 `not_found` |
| AI 상한, 거절, 실패 | 기존 429, 422 `ai_refused`, 502 `ai_unavailable` |
