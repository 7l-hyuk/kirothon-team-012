# 설계: AI 엔드포인트 실제 구현

## 구조

```
backend/
├── data/{illegal_parking,trash_dumping,illegal_ad,facility_damage}.json   # 절차 데이터 (기획서 값, verified:false)
└── app/
    ├── config.py              # is_mock(): 키가 비어 있으면 True
    ├── ai/
    │   ├── client.py          # Anthropic 클라이언트, parse_message(): 호출·refusal·오류 변환
    │   ├── prompts.py         # 한국어 프롬프트, 절차 데이터 렌더링
    │   └── analyze.py, review.py, rehearsal.py, draft.py   # 기능별 호출
    ├── schemas/ai_outputs.py  # AI 구조화 출력 모델 (모든 필드 필수, Literal)
    ├── services/
    │   ├── procedures.py      # JSON 로딩·검증, 서버 시작 때 실패 처리
    │   ├── typeinfo.py        # 유형 정보 조회: 가짜 모드는 mock 카탈로그, 실제 모드는 절차 데이터
    │   ├── store.py           # 메모리 저장소 (분석, 신고 건, 사진, AI 호출 수)
    │   ├── quota.py           # 기기별 하루 호출 상한
    │   ├── photos.py          # 업로드 검사, Pillow 축소, 사진 저장
    │   ├── guide.py           # 절차 데이터로 접수 안내 단계 조립
    │   └── assist.py          # 실제 모드의 분석·검수·사전 점검·대필
    ├── mock/                  # 가짜 응답과 공용 상태 로직 (service.py는 두 모드가 같이 씀)
    └── routers/               # 모드에 따라 mock/assist로 나눔. photos.py, procedures.py 추가
```

## 모드 분기

- 라우터가 `is_mock()`으로 가짜(`mock/service.py`)와 실제(`services/assist.py`)를 나눈다. 엔드포인트는 모두 `def`(스레드풀)다.
- 신고 건 조회·수정·목록·증거 체크리스트·접수 안내처럼 AI가 없는 로직은 `mock/service.py`를 두 모드가 같이 쓴다. 유형 정보는 `typeinfo.type_def()`로 얻는다.
- `X-Mock`은 미들웨어가 `is_mock()`일 때만 붙인다.
- 저장소는 `services/store.py`로 옮겼다. `mock/store.py`는 옛 import를 위한 재수출만 남긴다.

## AI 호출 (`ai/client.py`)

```python
client = anthropic.Anthropic(api_key=..., timeout=50.0, max_retries=0)
response = client.messages.parse(model=settings.claude_model, max_tokens=..., system=..., messages=[...], output_format=Model)
```

- `temperature`, `top_p`, `top_k`, `thinking`, `budget_tokens`, `tool_choice`, prefill은 보내지 않는다.
- `stop_reason == "refusal"`을 먼저 확인하고 `422 ai_refused`. `parsed_output`이 없거나 검증에 실패하면 `502`.
- 예외는 `APIConnectionError`, `RateLimitError`, `AuthenticationError`, `BadRequestError`, `APIStatusError` 순으로 잡아 모두 `502 ai_unavailable`로 바꾼다. 로그에는 종류와 상태 코드만 남긴다.
- 호출 전에 `quota.consume_ai_call()`로 기기별 호출 수를 센다. 실패한 호출도 센다(비용이 들기 때문).

## AI가 판단하는 것과 서버가 조립하는 것

| 엔드포인트 | AI | 서버 |
|---|---|---|
| 분석 | `summary`, 항목별 `reason`·`zone`(6대 금지구역 또는 `no_parking_zone`), `unsupported_items`, `not_reportable`, 위치, `emergency`, 증거 장면 충족 | `label`, `category`, `subtitle`(절차 데이터), 유형 밖 항목 이동, 사진 URL |
| 검수 | `status`, `message`, `retake_tip` | `retake_tip` 보충, 증거 진행 수 |
| 사전 점검 | `zone`, 3개 판정과 설명 | 라벨, `passed`, `capture_guide`, 간격(`interval_seconds`) |
| 대필 | 문구 | 위치 자리표시 보장, 저장 |

- 분석에서 받은 "사진이 충족하는 장면"은 `AnalysisRecord.scene_matches`에 저장한다. 신고 건을 만들 때 이를 `SceneState`에 반영하며 AI를 다시 부르지 않는다. 불법주정차는 사전 점검이 증거 단계라서 반영하지 않는다.
- 불법주정차 사전 점검에서 금지구역이 아니라고 판정되면 증거 단계를 완료 처리하지 않는다. 그 외에는 명세대로 점검만 해도 완료 처리한다.
- 분석 출력의 각 item은 `photo_numbers`(그 문제가 보이는 사진 번호, 1부터, 없으면 빈 목록)를 함께 준다. 서버가 범위 밖 번호와 중복을 걸러 사진 ID로 바꿔 `AnalysisRecord.item_photo_ids`(type_id → 사진 ID 목록)에 저장한다. API 응답에는 나가지 않는다.
- 사전 점검의 사진 선택 규칙: ① 요청에 `photo_id`가 있으면 그 사진(이 건의 사진이 아니면 404). ② 없으면 불법주정차 item의 첫 번째 사진. ③ 그것도 없으면 분석의 첫 사진. ④ 사진이 하나도 없으면 `422 validation_error`("사진을 먼저 올려 달라"는 해요체 문구).

## 사진

- `photos.py`: MIME 검사(415), 10MB 검사(413), Pillow로 열어 EXIF 회전 적용, 흰 배경 RGB 변환, 긴 변 1568px 이하로 축소, JPEG(품질 85) 저장. 열 수 없는 파일은 415.
- Pillow는 함수 안에서 불러온다. 가짜 모드는 Pillow 없이도 뜬다.
- 줄인 사진은 `store.photos[id]`에 기기 ID와 함께 둔다. `GET /api/photos/{id}/file`은 `<img>`가 헤더를 보내지 못해 `X-Device-Id`를 검사하지 않는다. 추측할 수 없는 UUID가 접근 열쇠다(임시, 다음 Spec에서 S3 presigned URL로 교체).
- 사진은 AI 호출이 성공한 뒤에 저장한다.

## 절차 데이터

`structure.md` 스키마에 아래를 더했다(모두 선택 필드).

- `outcome_note`: 체크박스 아래 한 줄의 앞부분. 예: "과태료 부과 대상". 없으면 `agency` + " 처리"를 쓴다.
- `eligibility.basis`: 신고 불가 안내의 근거 문장.
- `capture_rules.interval_note`, `capture_guide`(제목, 단계 템플릿, 경고), `zones[].first_shot_tip`: 사전 점검 안내 조립용.
- `steps[].body`: 단계 설명. `{photo_count}`는 서버가 채운다.

값은 기획서에 있는 것만 썼고, 안전신문고 화면과 대조하지 못했으므로 모든 파일과 단계에 `verified: false`를 둔다.

## 테스트

`app.ai.client.get_client`를 가짜 객체로 바꾼다(`messages.parse()`가 `parsed_output`, `stop_reason`을 가진 객체를 돌려줌). `conftest.py`는 매 테스트마다 키 환경변수를 지우고 작업 디렉터리를 임시 폴더로 옮겨 `.env`가 섞이지 않게 한다.
