# 작업 목록: 사례 공유 (백엔드)

## 1. Spec
- [x] 1.1 `requirements.md`, `design.md`, `tasks.md` 작성

## 2. 데이터
- [x] 2.1 `models/tables.py`: `Case`, `CaseLike`, `CasePhoto`, `CaseDraft` 추가(기존 테이블은 그대로), `models/__init__.py` 내보내기
- [x] 2.2 `schemas/cases.py`, `schemas/ai_outputs.py`(`CaseDraftOutput`)

## 3. AI
- [x] 3.1 `ai/prompts.py`: `case_system`, `case_user_text`
- [x] 3.2 `ai/case.py`: `run()`

## 4. 서비스와 라우터
- [x] 4.1 `services/cases.py`: scrub, facts, 고정 형식 글, 초안, 미리보기, 공유, 내리기, 목록, 상세, 좋아요
- [x] 4.2 `routers/cases.py`, `main.py` 등록
- [x] 4.3 `mock/service.py`: `report_out`의 `case_id`

## 5. 예시 사례
- [x] 5.1 `data/seed_cases.json` 3건
- [x] 5.2 `app/seed.py`, `main.lifespan`에서 호출

## 6. 테스트
- [x] 6.1 `tests/test_cases.py`: 409, 422, 중복 공유, 초안 재사용, 다른 기기, 좋아요, 필터, seed, 내리기, AI 입력 비식별화

## 7. 문서
- [x] 7.1 `docs/api-spec.md` 7, 8장 수정
- [x] 7.2 `structure.md` DB 테이블 수정

## 남은 일 (실행 검증)
셸 명령 없이 파일만 작성했으므로 아래는 아직 돌려 보지 않았습니다. 위 `[x]`는 "작성함"이지 "통과함"이 아닙니다.
- [ ] `cd backend && uv run pytest` (기존 104개 + `tests/test_cases.py`)
- [ ] 서버 DB(PostgreSQL)에서 `create_all`이 새 테이블 4개만 만들고 기존 테이블을 건드리지 않는지 확인
- [ ] 실제 Claude 호출로 사례 글의 길이·문체·비식별화 확인

## 알려진 한계
- 시작할 때 DB가 없어 `init_db()`가 실패하면 그 프로세스에서는 예시 사례를 넣지 않는다(다음 시작 때 넣는다).
- 비식별화 `scrub()`은 정규식이라 이름처럼 형태가 없는 값은 지우지 못한다. 불수용 사유 같은 사용자 입력 글에 이름이 있으면 프롬프트 규칙에 기댄다.
- 예시 사례는 응답에서 실제 사례와 구분되지 않는다(명세에 표시 필드가 없다).

## 코드 리뷰 반영
셸 없이 파일만 고쳤습니다. `[x]`는 "고쳐 작성함"이고, `uv run pytest`는 아직 돌려 보지 않았습니다.
- [x] 사전 점검 결과를 실제보다 좋게 쓰던 문제: 사전 점검 항목별 판정을 `reports.scenes`의 예약 키 `_rehearsal`(기존 JSON 컬럼)에 저장하고, AI 자료(`CaseFacts.rehearsal`)와 프롬프트에 넘김. 저장된 결과가 없으면 "사전 점검을 거쳤다"만 넘김. 프롬프트에 "충분 판정을 받지 않은 항목을 충분했다고 쓰지 않는다" 규칙 추가
- [x] 처리 기간 단정: `days_to_result`와 "걸린 일수"를 AI 자료·프롬프트·고정 형식 글에서 제거. 프롬프트에 기간 표현 금지 규칙 추가. 결과 절 본문은 결과(불수용이면 비식별화한 사유)만 씀
- [x] 미확인 메뉴 경로 단정: 절차 데이터가 `verified: false`면 `menu_path`를 빈 목록으로 넘기고 접수처 이름과 유형만 씀. `verified: true`일 때만 경로를 넘김
- [x] 예시 사례(`seed_cases.json`): 기간 표현은 없었고, 미확인 메뉴 이름("생활불편 신고")을 쓴 전단지 사례의 접수 문장을 "안전신문고 앱으로 접수했어요"로 고침
- [x] 테스트 추가(`tests/test_cases.py`): AI 입력에 걸린 일수와 미확인 메뉴 경로가 없음, 검증된 경로는 넘어감, 사전 점검 항목별 판정이 넘어감, 저장된 결과가 없으면 거쳤다는 사실만 넘어감
- [x] 프론트 인수인계(PR #9) 반영: 가짜 모드 사전 점검도 실제 모드와 같은 사진 선택 규칙(`select_rehearsal_photo`)을 거쳐, 쓸 사진이 없으면 422를 돌려줌. `tests/test_mock_flow.py`에 테스트 추가
