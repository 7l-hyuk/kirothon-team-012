# 요구사항: 백엔드 뼈대와 가짜(mock) API

프론트 담당자가 실제 AI·DB·S3 없이 시연 흐름(S1~S9)을 끝까지 붙여 볼 수 있도록, 명세(`docs/api-spec.md`)와 같은 모양의 고정 응답 API와 배포 가능한 뼈대를 만든다. 실제 구현은 다음 Spec에서 한다.

## 사용자 스토리

1. 프론트 개발자로서, 명세와 같은 경로·응답 모양의 가짜 API를 받고 싶다. 백엔드가 완성되기 전에 화면을 만들 수 있어야 한다.
2. 시연 진행자로서, 재촬영 흐름(불충분 → 충분)과 신고 불가 흐름(아파트 주차장)을 항상 같은 결과로 보여 주고 싶다.
3. 배포 담당자로서, `main`에 push하면 `deploy/deploy.sh`가 `docker compose up`으로 앱과 DB를 띄우고 `/api/health`가 응답하길 원한다.
4. 백엔드 개발자로서, `ai/`, `storage/`, `services/`, `data/` 자리가 잡힌 구조에서 다음 Spec을 이어서 구현하고 싶다.

## 인수 조건 (EARS)

### 공통
- 모든 `/api` 요청(`/api/health`, `/api/mock/placeholder.svg` 제외)에 `X-Device-Id`가 없거나 UUID 형식이 아니면, 시스템은 `400 {"detail","code":"missing_device_id"}`로 응답해야 한다.
- 오류가 발생하면, 시스템은 항상 `{"detail": "해요체 문구", "code": "snake_case"}` 형태로 응답해야 한다.
- 다른 기기의 리소스를 요청하면, 시스템은 `404 not_found`로 응답해야 한다.
- 시스템은 모든 `/api` 응답에 `X-Mock: true` 헤더를 넣어야 한다.
- 가짜 API는 Anthropic API, DB, S3를 호출하지 않아야 하고, 상태는 프로세스 메모리에만 둬야 한다.

### 서버 상태와 정적 파일
- `GET /api/health`가 호출되면, 시스템은 DB 연결 여부와 관계없이 `200 {"status":"ok","db":"ok"|"unavailable","mock":true}`로 응답해야 한다.
- DB 연결에 실패해도, 시스템은 기동을 멈추지 않아야 한다.
- `STATIC_DIR`에 `index.html`이 있으면, 시스템은 정적 파일을 서빙하고 `/api`로 시작하지 않는 알 수 없는 경로를 `index.html`로 응답해야 한다.
- `STATIC_DIR`에 `index.html`이 없으면, `GET /`는 `{"service":"shingomate","docs":"/docs"}`로 응답해야 한다.
- `.env` 없이도 모든 설정은 로컬 기본값으로 기동해야 한다.

### 상황 분석
- `text`에 "아파트" 또는 "주차장"이 들어 있으면, `POST /api/analyses`는 명세의 신고 불가 응답(시나리오 B)을 `201`로 돌려줘야 한다.
- 그 외 입력이면, 같은 API는 불법주정차 + 쓰레기 무단투기 2건 응답(시나리오 A)을 돌려줘야 한다.
- `text`와 `photos`가 모두 없으면, 시스템은 `422 validation_error`로 응답해야 한다.
- 지원하지 않는 사진 형식은 `415`, 10MB 초과는 `413`으로 응답해야 한다.
- `GET /api/analyses/{id}`는 생성 때와 같은 본문을 돌려줘야 한다.

### 신고 건
- `type_ids`를 보내면, 시스템은 보낸 순서대로 `sequence`를 매긴 신고 건을 만들어야 한다.
- 분석 결과에 없는 `type_id`나 중복 값이 오면, 시스템은 `422`로 응답해야 한다.
- 같은 분석에서 신고 건을 이미 만들었으면, 시스템은 `409 invalid_state`로 응답해야 한다.
- `PATCH`로 `status`를 거꾸로 보내거나 필수 증거가 부족한 채 `filed`로 바꾸려 하면, 시스템은 `409`로 응답해야 한다.
- `result`가 `accepted`나 `rejected`이면, 시스템은 `status`를 `resolved`로 바꿔야 한다.
- `GET /api/reports`는 요청한 기기의 건만 최신순으로 돌려주고 `status`, `limit`을 적용해야 한다.

### 증거와 사전 점검
- 같은 장면에 사진을 처음 올리면, 시스템은 `insufficient`와 `retake_tip`을 돌려줘야 한다.
- 같은 장면에 두 번째로 올리면, 시스템은 `sufficient`를 돌려줘야 한다.
- 업로드된 사진 파일은 저장하지 않아야 한다.
- 불법주정차가 아닌 건에 `POST /rehearsals`를 호출하면, 시스템은 `409`로 응답해야 한다.
- 사전 점검이 호출되면, 시스템은 불법주정차 건의 증거 장면을 완료 처리해야 한다.

### 접수 안내와 문구
- `GET /guide`는 7단계를 돌려줘야 한다.
- 건의 `sequence`가 2 이상이면, 시스템은 `carry_over`를 채우고 로그인·접속·위치 단계를 `skipped: true`로 표시해야 한다.
- `POST /drafts`는 `tone`(`default`/`shorter`/`politer`)별 고정 문구를 돌려주고 건의 `draft_text`에 저장해야 한다.

### 사진 자리표시
- 모든 사진 `url`은 `/api/mock/placeholder.svg`여야 하고, 이 경로는 회색 줄무늬 SVG를 돌려줘야 한다.

### 배포
- `docker compose --env-file /opt/shingomate/.env up -d --build`가 실행되면, `app`은 `db`가 healthy가 된 뒤 8000번 포트로 뜨고 호스트 `APP_PORT`(기본 80)에 연결돼야 한다.
- `frontend/package.json`이 없어도 Docker 빌드는 성공해야 한다.
- 컨테이너는 root가 아닌 사용자로 실행해야 한다.
- DB 포트는 `127.0.0.1`로만 열어야 한다.
