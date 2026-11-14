# 작업 목록: 백엔드 뼈대와 가짜(mock) API

## 1. 프로젝트 설정
- [x] 1.1 `backend/pyproject.toml` (uv, Python >=3.13, 의존성, dev 그룹)
- [x] 1.2 `backend/.env.example`
- [x] 1.3 `app/config.py` 환경변수 설정

## 2. 공통 기반
- [x] 2.1 `app/errors.py` 오류 코드와 처리기
- [x] 2.2 `app/deps.py` `X-Device-Id` 검사
- [x] 2.3 `app/db.py` 엔진과 `check_db()`
- [x] 2.4 `app/schemas/` 명세의 요청·응답 모델

## 3. 가짜 API
- [x] 3.1 `app/mock/` 카탈로그, 고정 응답, 메모리 저장소, 서비스
- [x] 3.2 `app/routers/analyses.py`
- [x] 3.3 `app/routers/reports.py`
- [x] 3.4 `app/routers/assets.py` (`placeholder.svg`)
- [x] 3.5 `app/main.py` (health, X-Mock, SPA 서빙)

## 4. 빈 자리 패키지
- [x] 4.1 `app/ai/`, `app/storage/`, `app/services/`, `app/models/`, `data/`

## 5. 테스트
- [x] 5.1 health, 기기 ID 400
- [x] 5.2 분석 → 신고 건 → 증거 → 안내 흐름
- [x] 5.3 PATCH 전이, 타 기기 404, SPA

## 6. 배포
- [x] 6.1 `Dockerfile` (멀티 스테이지, 비root)
- [x] 6.2 `.dockerignore`
- [x] 6.3 `docker-compose.yml` (`db`, `app`)

## 남은 일 (실행 검증)
셸 실행 없이 작성했으므로 아래는 아직 돌려 보지 않았습니다.
- [ ] `cd backend && uv sync && uv run pytest`
- [ ] `docker compose build` 와 `/api/health` 확인
- [ ] `uv.lock` 생성 후 커밋

## 코드 리뷰 반영
- [x] 7.1 `docker-compose.yml`: db 호스트 포트를 `127.0.0.1:${DB_PORT:-5432}`로 바꾸고 `DB_PORT`, `APP_PORT` 안내 주석 추가
- [x] 7.2 `Dockerfile`: `uv.lock`을 복사하고 `uv sync --frozen --no-dev --no-install-project`로 설치
- [x] 7.3 `tech.md`: Python 버전을 3.13 이상으로 고치고 이유 기록
- [x] 7.4 `app/mock/fixtures.py`: 대필 문구의 문체를 합니다체로 통일
- [x] 7.5 `design.md`에 포트 변수와 `--frozen` 설치 반영
