# 요구사항: 메모리 상태를 PostgreSQL과 S3로 옮기기

`ai-assist` Spec까지 프로세스 메모리에 두던 분석, 신고 건, 사진, AI 호출 수를 PostgreSQL(SQLModel)과 사진 저장소(S3 또는 로컬 디스크)로 옮긴다. API 경로와 요청·응답 형태는 그대로다. 달라지는 것은 사진 `url`의 값, `health` 응답의 `storage` 필드, 새 오류 코드 두 개뿐이다. 사례 API(`cases`)는 이번 범위가 아니다.

## 사용자 스토리

1. 사용자로서, 서버가 재시작되거나 새로 배포돼도 내 분석과 신고 건이 남아 있길 원한다. 이어서 신고하기 위해서다.
2. 사용자로서, 올린 사진이 재시작 뒤에도 보이길 원한다. 접수할 때 다시 찍지 않기 위해서다.
3. 운영자로서, 기기당 하루 AI 호출 수가 재시작해도 초기화되지 않길 원한다. 상한을 우회하지 못하게 하기 위해서다.
4. 운영자로서, 사진을 비공개 S3 버킷에 두고 URL은 요청 때마다 만료 시간이 있는 주소로 받길 원한다.
5. 프론트 개발자로서, 키가 없는 가짜 모드와 API 형태가 그대로이길 원한다.
6. 운영자로서, DB가 늦게 뜨거나 죽어 있어도 앱은 뜨고 오류는 일관된 형태로 받길 원한다.

## 인수 조건 (EARS)

### 저장과 소유권
- 시스템은 분석, 신고 건, 사진, AI 호출 수를 `analyses`, `reports`, `photos`, `ai_usage` 테이블에 저장해야 한다. 메모리 저장소는 남기지 않는다.
- 시스템은 모든 조회와 수정에 `device_id` 조건을 걸어야 한다. 다른 기기의 리소스는 `404 not_found`로 응답해야 한다.
- 앱(엔진)을 새로 만들어도, 시스템은 같은 DB의 분석과 신고 건을 조회할 수 있어야 한다.
- `ANTHROPIC_API_KEY`가 없는 가짜 모드에서도, 시스템은 분석과 신고 건을 DB에 저장해야 한다. 가짜 응답의 값과 `X-Mock: true`는 그대로여야 한다.
- 시각은 timezone이 있는 값으로 저장하고, 응답은 KST 오프셋(`+09:00`)으로 내야 한다.
- 구조가 깊은 값(AI 분석 결과, 증거 장면 상태)은 `sqlalchemy.JSON` 컬럼에 두고, JSONB·ARRAY 같은 PostgreSQL 전용 타입은 쓰지 않아야 한다.
- 같은 분석에서 같은 `sequence`의 신고 건이 둘 만들어지지 않아야 한다. 동시에 두 번 만들면 한쪽은 `409 invalid_state`다.

### DB 연결
- 앱이 시작될 때, 시스템은 `SQLModel.metadata.create_all`로 테이블을 만들어야 한다. 마이그레이션 도구는 쓰지 않는다.
- DB에 연결하지 못하면, 시스템은 2초 간격으로 최대 15번 다시 시도해야 한다.
- 끝내 연결하지 못해도, 시스템은 앱을 띄워야 한다. 이때 DB가 필요한 요청은 `503`(`code: db_unavailable`, 해요체 문구)으로 응답해야 한다.
- 이후 DB가 살아나면, 시스템은 재시작 없이 테이블을 만들고 요청을 처리해야 한다.
- 요청 중 DB 연결이 끊기면, 시스템은 `503 db_unavailable`로 응답하고 로그에는 오류 종류만 남겨야 한다.
- 세션은 요청 단위로 열고 닫아야 한다. 엔드포인트는 동기 `def`로 둔다.
- `GET /api/health`는 DB 연결을 실제로 확인해 `db`에 `ok` 또는 `unavailable`을 돌려주고, `storage`에 `s3` 또는 `local`을 돌려줘야 한다. DB가 죽어 있어도 `200`이다.

### AI 호출 수
- 시스템은 `ai_usage`에 `(device_id, day)` 유일 제약을 두고, `day`는 KST 날짜로 해야 한다.
- 호출 수 증가와 상한 검사는 한 트랜잭션에서 처리해야 한다. 같은 기기가 동시에 불러도 상한을 넘기지 않는다.
- 날짜가 바뀌면, 시스템은 날짜별로 따로 세어야 한다.
- 상한에 이르면 `429 daily_limit_exceeded`, 가짜 모드에서는 세지 않는 동작은 그대로여야 한다.

### 사진 저장소
- 시스템은 저장소 인터페이스 하나와 구현 둘(`S3Storage`, `LocalStorage`)을 둬야 한다. 라우터와 서비스는 구현을 직접 부르지 않는다.
- `S3_BUCKET`이 있으면 `S3Storage`, 없으면 `LocalStorage`(`UPLOAD_DIR`)를 써야 한다.
- 시스템은 사진을 긴 변 1568px 이하 JPEG로 줄여 `photos/{yyyy}/{mm}/{photo_id}.jpg` 키로 저장하고, DB에는 키만 둬야 한다. URL은 저장하지 않는다.
- `S3Storage`는 `boto3`의 `put_object`로 올리고 `generate_presigned_url("get_object", ...)`로 조회 주소를 만들어야 한다. 만료는 `PRESIGN_EXPIRES_SECONDS`다.
- `S3Storage`는 자격 증명을 코드나 환경변수로 받지 않고(EC2 IAM 역할을 boto3가 찾는다), ACL을 지정하지 않아야 한다.
- `LocalStorage`일 때 사진 `url`은 `GET /api/photos/{photo_id}/file`이어야 한다. 이 경로는 `S3Storage`일 때 `404`다.
- 사전 점검이 분석 때 올린 사진을 다시 쓸 때, 시스템은 저장소에서 바이트를 다시 읽어 AI에 보내야 한다.
- S3 오류(`ClientError`, `BotoCoreError`)가 나면, 시스템은 `502 storage_unavailable`로 응답하고 로그에는 오류 종류만 남겨야 한다.
- 같은 장면에 사진을 다시 올리면, 시스템은 증거 장면이 새 사진을 가리키게 해야 하고 이전 사진은 건의 사진 목록에서 빠져야 한다.
- 가짜 모드는 파일을 저장하지 않고, 사진 `url`은 `/api/mock/placeholder.svg` 그대로여야 한다.

### 문서와 설정
- 시스템은 `docs/api-spec.md`의 오류 코드 표, health 응답, 사진 파일 절을 위 동작에 맞게 갖춰야 한다.
- `backend/.env.example`은 새 설정을 포함해야 한다.
- 새 의존성이 필요하면 `pyproject.toml`에만 추가한다.

### 테스트
- 테스트는 SQLite 메모리 DB와 임시 폴더의 `LocalStorage`로 돌고, PostgreSQL, S3, Anthropic에 접속하지 않아야 한다.
- `S3Storage`는 가짜 boto3 클라이언트로 키 형식, presigned URL 호출 인자, 오류 변환을 검증해야 한다.
