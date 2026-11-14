# 작업 목록: PostgreSQL과 S3 저장

## 1. Spec
- [x] 1.1 `requirements.md`, `design.md`, `tasks.md` 작성

## 2. 기반
- [x] 2.1 `app/timeutil.py`, `app/models/types.py`(KSTDateTime)
- [x] 2.2 `app/models/tables.py`: `analyses`, `reports`, `photos`, `ai_usage`
- [x] 2.3 `app/errors.py`: `db_unavailable`(503), `storage_unavailable`(502), DB 연결 오류 처리기
- [x] 2.4 `app/db.py`: 엔진, `create_tables`, `init_db`(2초×15), `ensure_ready`, `check_db`
- [x] 2.5 `app/deps.py`: `SessionDep`

## 3. 사진 저장소
- [x] 3.1 `app/storage/base.py`, `local.py`, `s3.py`, `__init__.py`(`get_storage`, `storage_kind`)
- [x] 3.2 `app/services/photos.py`에서 메모리 저장 제거(검사·축소만 남김)

## 4. 저장소와 서비스
- [x] 4.1 `app/services/store.py`를 DB 구현으로 교체(분석, 신고 건, 장면 상태, 사진 행). `app/mock/store.py`는 빈 모듈
- [x] 4.2 `app/services/quota.py`: `ai_usage` 원자적 증가, KST 날짜
- [x] 4.3 `app/mock/service.py`: 세션을 받아 DB 사용
- [x] 4.4 `app/services/assist.py`: 세션, 저장소 사용, 사전 점검은 저장소에서 다시 읽기
- [x] 4.5 라우터에 `SessionDep` 연결, `GET /api/photos/{id}/file`은 `LocalStorage`일 때만
- [x] 4.6 `app/main.py`: `lifespan`에서 `init_db`, `health`에 실제 DB 상태와 `storage`

## 5. 배포 파일과 설정
- [x] 5.1 `docker-compose.yml`에 `uploads` 볼륨 (`Dockerfile`은 이미 `/app/uploads`를 `app` 사용자 소유로 만들어 두어 바꾸지 않음)
- [x] 5.2 `backend/.env.example`, `pyproject.toml`(새 의존성 없음 확인, 설명 문구만 수정)

## 6. 테스트
- [x] 6.1 `conftest.py`: SQLite 메모리 DB, 임시 폴더 `LocalStorage`
- [x] 6.2 기존 테스트의 저장소 직접 접근을 DB 도우미로 교체, `health` 기대값에 `storage` 추가
- [x] 6.3 `test_persistence.py`: 엔진 재생성 후 조회, 다른 기기 404, 날짜별 호출 수, 503과 복구, 재시도, 사진 대체, KST 오프셋
- [x] 6.4 `test_storage.py`: `S3Storage`(가짜 클라이언트) 키·presign 인자·오류 변환, `LocalStorage`, 사진 파일 경로

## 7. 문서
- [x] 7.1 `docs/api-spec.md`: 오류 코드 표, health, 사진 파일 절
- [x] 7.2 `tech.md`, `structure.md`에서 달라진 부분만 수정

## 남은 일 (실행 검증)
셸 명령 없이 파일만 작성했으므로 아래는 아직 돌려 보지 않았습니다.
- [ ] `cd backend && uv run pytest` (기존 59개 + 새 테스트)
- [ ] `docker compose up -d --build`로 앱과 DB를 띄우고 `docker compose restart app` 뒤에 신고 건이 남는지 확인
- [ ] 실제 S3 버킷과 EC2 IAM 역할로 사진 업로드, presigned URL 열기 확인 (역할에 `s3:PutObject`, `s3:GetObject` 필요)
- [ ] `git rm backend/app/mock/store.py`
- [ ] `uv.lock` 갱신(`ai-assist` Spec에서 추가한 `pillow`가 아직 잠금 파일에 없을 수 있음)

## 코드 리뷰 반영
- [x] 분석 프롬프트(`app/ai/prompts.py`)에서 `photo_numbers`(문제가 보이는 사진)와 `satisfied_scenes`(증거 장면 통과 기준 충족)를 구분하고, "애매하면 넣지 않습니다"를 "통과 기준에 적힌 것이 사진에 분명히 보이면 넣는다"로 변경. `schemas/ai_outputs.py` 필드 주석도 같은 뜻으로 맞춤
