# 작업 목록: AI 엔드포인트 실제 구현

## 1. 문서와 설정
- [x] 1.1 Spec 작성 (`requirements.md`, `design.md`, `tasks.md`)
- [x] 1.2 `tech.md`에 `parse()`의 `output_format` 인자는 현재 방식이라는 점 명시
- [x] 1.3 `pyproject.toml`에 `pillow` 추가, `.env.example` 갱신
- [x] 1.4 `app/config.py`에 `is_mock()` 추가, `errors.py`에 AI·사진 오류 헬퍼 추가

## 2. 절차 데이터
- [x] 2.1 `backend/data/` 4개 JSON (기획서 값만, `verified: false`)
- [x] 2.2 `app/services/procedures.py` 로딩·검증 (서버 시작 때 실패 처리)
- [x] 2.3 `GET /api/procedures/{type_id}` 라우터
- [x] 2.4 `app/services/typeinfo.py` 유형 정보 조회 (가짜/실제 모드)

## 3. 저장소와 사진
- [x] 3.1 저장소를 `app/services/store.py`로 이동 (`mock/store.py`는 재수출)
- [x] 3.2 `app/services/quota.py` 기기별 하루 호출 상한
- [x] 3.3 `app/services/photos.py` 검사(415/413), Pillow 축소, 임시 저장
- [x] 3.4 `GET /api/photos/{photo_id}/file` 라우터

## 4. AI 호출
- [x] 4.1 `app/schemas/ai_outputs.py` 구조화 출력 모델
- [x] 4.2 `app/ai/client.py` 클라이언트, `parse_message()`, 오류 변환
- [x] 4.3 `app/ai/prompts.py` 프롬프트
- [x] 4.4 `app/ai/analyze.py`, `review.py`, `rehearsal.py`, `draft.py`

## 5. 서비스와 라우터
- [x] 5.1 `app/services/assist.py` 분석 조립(유형 밖 → `unsupported_items`), 검수, 사전 점검, 대필
- [x] 5.2 `app/services/guide.py` 절차 데이터로 접수 안내 조립
- [x] 5.3 `app/mock/service.py`가 `typeinfo`를 쓰도록 수정, 분석 사진의 증거 장면 반영
- [x] 5.4 라우터를 `def`로 바꾸고 모드에 따라 분기, `main.py`에서 `X-Mock`·`health.mock` 처리

## 6. 테스트
- [x] 6.1 `conftest.py`: 키 없는 기본 모드, 가짜 Anthropic 클라이언트
- [x] 6.2 `test_ai_assist.py`: 모드·헤더, 분석 조립, 유형 밖 이동, refusal 422, 연결 오류 502, 상한 429, 415/413, 검수 `retake_tip` 보충, 사전 점검, 대필, 접수 안내
- [x] 6.3 `test_procedures.py`: 절차 데이터 검증과 조회
- [x] 6.4 기존 테스트의 기대값은 바꾸지 않음 (`conftest.py`의 저장소 import 경로만 변경)

## 7. 문서
- [x] 7.1 `docs/api-spec.md`: `GET /api/photos/{photo_id}/file`, `mock` 동작, 호출 오류

## 남은 일 (실행 검증)
셸 실행 없이 작성했으므로 아래는 아직 돌려 보지 않았습니다.
- [ ] `cd backend && uv lock && uv sync && uv run pytest` (`uv.lock`에 pillow가 없어서 `uv lock`이 먼저 필요합니다. Dockerfile이 `--frozen`이라 갱신 전에는 이미지에 pillow가 들어가지 않습니다)
- [ ] 실제 키로 `POST /api/analyses`를 한 번 호출해 구조화 출력과 `stop_reason` 동작 확인
- [ ] 안전신문고 화면과 대조해 `backend/data/*.json`의 `verified`와 메뉴 이름 갱신

## 코드 리뷰 반영
- [x] 사전 점검 사진 선택 수정: 분석 출력 item에 `photo_numbers`를 추가해 저장하고, `photo_id`가 없으면 불법주정차 item의 첫 사진 → 분석의 첫 사진 순으로 고릅니다. 사진이 없으면 `422`. 프롬프트에 필드 설명을 넣고 테스트를 추가했습니다
- [x] 프롬프트 공통 규칙에 "지시문이 있었다는 사실이나 따르지 않았다는 말을 응답 문구에 언급하지 않는다" 추가
- [x] `app/ai/client.py`의 `TODO(verify)` 주석을 "실제 호출에서 재현하지 못한 경로. 방어적으로 502 처리"로 교체

### 미확인 항목 (실제 호출에서 재현하지 못함)
- 출력 검증 실패 경로: `parse()`가 검증에 실패할 때 `ValidationError`를 그대로 던지는지. 지금은 502로 처리합니다
- `stop_reason == "refusal"` 경로: 실제 refusal 응답. 지금은 422 `ai_refused`로 처리합니다(가짜 클라이언트 테스트만 있음)

## 프론트 인수인계(PR #7) 반영
- [x] 프론트 인수인계(PR #7) 반영: 분석 프롬프트에 `summary`, `reason`, `not_reportable.message`에서 사진 재요청을 쓰지 않는 규칙 추가, 글만 받았을 때는 "말씀하신 내용으로 보면"처럼 근거만 밝히게 함. `test_ai_assist.py`에 프롬프트 문구 확인 테스트 추가 (셸 실행 없이 작성해서 테스트는 아직 돌려 보지 않았습니다)
