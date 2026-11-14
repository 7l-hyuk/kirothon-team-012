# 설계: 백엔드 뼈대와 가짜(mock) API

## 구조

```
backend/
├── pyproject.toml          # uv, requires-python >=3.13
├── .env.example
├── app/
│   ├── main.py             # create_app(): 라우터, 오류 처리기, X-Mock 미들웨어, health, SPA 서빙
│   ├── config.py           # pydantic-settings. 모든 값에 로컬 기본값. 빈 값은 기본값으로 대체
│   ├── deps.py             # X-Device-Id 검사 (DeviceId 의존성)
│   ├── errors.py           # ApiError, 오류 코드, 공통 처리기
│   ├── db.py               # 지연 생성 엔진, check_db()
│   ├── schemas/            # 명세의 요청·응답 Pydantic 모델
│   ├── routers/            # analyses.py, reports.py, assets.py(placeholder.svg). 얇게 유지
│   ├── mock/               # 가짜 응답 데이터와 메모리 저장소 (다음 Spec에서 통째로 교체)
│   │   ├── catalog.py      # 유형별 라벨, 메뉴 경로, 증거 장면 (명세 예시 값)
│   │   ├── fixtures.py     # 분석 응답 A/B, 사전 점검, 문구, SVG
│   │   ├── store.py        # 프로세스 메모리 저장소
│   │   └── service.py      # 상태 전이, 응답 조립
│   ├── ai/ storage/ services/   # 빈 패키지 + 역할 주석
└── data/                   # 신고 절차 JSON 자리 (README만)
```

## 가짜 응답 방식

- 라우터는 검증과 응답 변환만 하고, 로직은 `mock/service.py`에 둔다. 다음 Spec에서 `services/`, `ai/`, `storage/`로 교체하면 라우터와 스키마는 그대로 쓴다.
- 엔드포인트는 `async def`로 만들어 메모리 저장소를 한 스레드에서만 만진다. 잠금이 필요 없다.
- 저장소: `store.analyses`, `store.reports` 두 dict. 기기 ID로 소유권을 확인하고 다르면 `404`.
- 분석 시나리오: `text`에 "아파트" 또는 "주차장"이 있으면 B, 아니면 A. 응답 값은 `docs/api-spec.md` 예시를 그대로 쓴다.
- 증거 장면은 건마다 `SceneState(photo, review, attempts)`로 관리한다. 업로드 때 `attempts`를 올려 1회차 `insufficient`, 2회차 이후 `sufficient`를 돌려준다. 분석 사진이 있으면 쓰레기 건의 `overview`는 처음부터 충족으로 둔다(명세의 사진 재사용).
- 불법주정차 건은 장면 1개(`vehicle`)이고, 사전 점검을 호출하면 충족 처리한다(명세: 사전 점검만으로 증거 단계 완료).
- `PATCH` 규칙: `preparing → filed → resolved` 순서만, `filed`는 필수 장면 충족 필요, `accepted`/`rejected`는 `resolved`로 전이.
- 가이드는 7단계(접속, 로그인, 메뉴, 사진, 위치, 내용, 접수)로 고정. `sequence >= 2`이면 1·2·5단계를 `skipped`로, `carry_over` 3줄을 채운다.
- 사진 `url`은 전부 `/api/mock/placeholder.svg`. 업로드 파일은 형식·크기만 검사하고 버린다.
- `X-Mock: true`는 `/api`로 시작하는 모든 응답에 미들웨어로 붙인다.

## 오류 처리

`ApiError(status, code, detail)`를 처리기로 `{"detail","code"}`에 변환한다. FastAPI의 검증 오류(`422 validation_error`)와 404/405 같은 HTTP 오류, 처리되지 않은 예외도 같은 형태로 바꾼다. 기기 ID 검사는 의존성에서 예외를 던져 본문 검증보다 먼저 `400`이 나간다.

## DB

`db.py`는 엔진을 처음 쓸 때 만들고 `connect_timeout=2`를 둔다. `check_db()`는 `SELECT 1` 성공 여부만 돌려준다. 테이블과 seed는 만들지 않는다(다음 Spec). 연결 실패는 기동에 영향이 없다.

## 배포 연결

```
push main → deploy.sh → docker compose --env-file /opt/shingomate/.env up -d --build
                         → app(8000 → 호스트 80) 이 db healthy 후 기동 → curl localhost/api/health
```

- `Dockerfile` 1단계(`node:24-slim`)는 `frontend/package.json`이 있으면 `npm ci && npm run build`, 없으면 빈 `frontend/dist`만 만든다. 2단계(`python:3.13-slim`)는 `backend/uv.lock`을 함께 복사해 `uv sync --frozen --no-dev --no-install-project`로 잠긴 버전만 설치하고 `dist`를 `/app/static`으로 복사한다. 비root 사용자로 `uvicorn`을 실행한다.
- `docker-compose.yml`의 `app.environment`에 `${VAR:-기본값}`을 하나씩 적는다. `--env-file`의 값은 이렇게 적어야 컨테이너에 들어간다.
- 호스트 포트는 `DB_PORT`(db, 기본 5432, `127.0.0.1`에만 바인딩)와 `APP_PORT`(app, 기본 80)로 바꾼다. 개발 PC의 PostgreSQL과 겹칠 때 쓴다.
- `DATABASE_URL` 기본값은 컨테이너 내부 주소(`db:5432`). 로컬 개발(uv 직접 실행)은 `config.py` 기본값 `localhost`를 쓴다.
- 서버 `.env`의 `POSTGRES_*`는 `db`가 읽고, `config.py`는 모르는 변수를 무시한다.
- `/api/health`는 DB가 죽어도 200이므로 배포 스크립트의 상태 확인이 DB 지연에 막히지 않는다.

## 테스트

`TestClient`로 `app`을 직접 호출한다. Anthropic·DB·S3는 쓰지 않는다(DB 확인은 `monkeypatch`). 케이스: health, 기기 ID 400, 분석 A/B/422, 신고 건 생성, 증거 재촬영, 사전 점검, 가이드 건너뛰기, 문구, PATCH 전이, 타 기기 404, SPA 서빙.
