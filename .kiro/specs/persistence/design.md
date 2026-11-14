# 설계: PostgreSQL과 S3 저장

## 구조

```
backend/app/
├── timeutil.py            # KST, now_kst(), today_kst()
├── db.py                  # 엔진, create_tables, init_db(재시도), ensure_ready(), check_db()
├── deps.py                # DeviceId, SessionDep(요청 단위 세션, DB 준비 확인)
├── models/
│   ├── types.py           # KSTDateTime: 저장은 UTC, 읽을 때 KST
│   └── tables.py          # Analysis, Report, Photo, AiUsage
├── storage/
│   ├── base.py            # Storage 인터페이스(kind, put, get, url)
│   ├── s3.py              # S3Storage (boto3)
│   ├── local.py           # LocalStorage (UPLOAD_DIR)
│   └── __init__.py        # get_storage(), storage_kind()
└── services/
    ├── store.py           # DB 저장소. 메모리 구현을 대체
    ├── quota.py           # ai_usage 원자적 증가
    └── photos.py          # 업로드 검사와 축소만 남김
```

`app/mock/store.py`(옛 import 재수출)는 쓰지 않는 빈 모듈로 바꾼다. 파일 삭제는 사람이 `git rm`으로 한다.

## 테이블

`structure.md` 초안과 `docs/api-spec.md`의 필드 이름을 따른다. 문자열 PK(UUID 문자열)를 쓴다. 명세의 ID가 UUID 문자열이고, 잘못된 형식의 ID도 `404`로 응답해야 해서 DB UUID 타입을 쓰지 않는다.

| 테이블 | 컬럼 (초안에서 더하거나 바꾼 것 표시) |
|---|---|
| `analyses` | `id`, `device_id`, `situation_text`, `result`(JSON), `address`, `district`, `dong`, `created_at`, **`scene_matches`(JSON)**, **`item_photo_ids`(JSON)** |
| `reports` | 초안 컬럼 + **`category`, `label`, `total`, `zone`, `scenes`(JSON)**, `location_text`는 위치의 address, **`district`, `dong`** |
| `photos` | 초안 그대로. `s3_key`는 가짜 모드 자리표시 사진에서 `NULL` |
| `ai_usage` | `id`, `device_id`, `day`(KST 날짜), `count`. `(device_id, day)` 유일 |

- `analyses.result`: `AnalysisResponse`에서 `id`, `created_at`, `input`을 뺀 나머지. `input.photos`는 `photos`(`analysis_id`, `taken_order`)에서 읽어 URL을 만든다. URL이 JSON에 남지 않는다.
- `reports.scenes`: `{scene_id: {photo_id, review, attempts}}`. 같은 분석 사진이 여러 건의 장면을 충족할 수 있고(응답의 사진 ID가 분석 사진 ID와 같아야 한다), 장면별 검수 결과는 사진 한 장이 아니라 (건, 장면) 단위라서 건에 둔다. `photos.scene_id`와 `review_*`는 업로드 때 받은 결과의 기록이다.
- `reports.(analysis_id, sequence)` 유일 제약으로 건 생성 경쟁을 막는다.
- `scene_id`가 없는 업로드 사진은 `photos.report_id`가 있고 `scene_id`가 `NULL`인 행이다(옛 `extra_photos`).
- FK: `reports.analysis_id`, `photos.analysis_id`, `photos.report_id`. 부모를 먼저 `flush`한 뒤 자식을 넣는다.
- JSON 컬럼은 항상 새 dict를 대입해 변경을 감지시킨다.
- 가짜 모드의 자리표시 사진도 `photos` 행(`s3_key = NULL`)으로 남긴다. 응답의 사진 ID가 서로 일치해야 하고(사전 점검, 증거 장면), URL은 `/api/mock/placeholder.svg`로 만든다.

## 시각

`KSTDateTime`(TypeDecorator, `DateTime(timezone=True)`): 쓸 때 UTC로 바꿔 저장하고, 읽을 때 KST로 돌려준다. SQLite는 timezone을 저장하지 못해 UTC로 간주한다. 그래서 응답 조립 코드는 `+09:00` 값을 그대로 쓴다.

## DB 연결 (`db.py`)

- `init_db()`: `create_tables`를 2초 간격으로 최대 15번 시도. 성공하면 준비 완료 표시. 실패해도 예외를 던지지 않고 `False`. 앱 `lifespan`에서 스레드로 부른다.
- `ensure_ready()`: `SessionDep`가 부른다. 준비 전이면 `create_tables`를 한 번 시도하되 2초 안에는 다시 시도하지 않는다. 실패하면 `503 db_unavailable`. DB가 늦게 살아나면 재시작 없이 복구된다.
- 요청 중 `OperationalError`, `InterfaceError`는 오류 처리기가 `503 db_unavailable`로 바꾼다.
- `SessionDep`: `Session(engine, expire_on_commit=False)`를 요청마다 열고 닫는다. 커밋은 쓰기 서비스가 직접 한다(`yield` 의존성의 종료 시점이 응답 전후로 버전마다 달라 거기에 의존하지 않는다).
- 엔진은 `postgresql+psycopg`이면 `connect_timeout=2`, SQLite URL이면 `check_same_thread=False`.

## AI 호출 수 (`quota.py`)

```
UPDATE ai_usage SET count = count + 1 WHERE device_id=? AND day=? AND count < :limit   -- 1행이면 통과
```
0행이면 행이 있는지 본다. 있으면 상한 도달(`429`). 없으면 `count=1`로 INSERT하고, 유일 제약 충돌이면(동시 요청) UPDATE를 한 번 더 한다. 증가는 곧바로 커밋한다. 호출이 이후에 실패해도 센다(비용이 들기 때문). 호출 전에 읽기만 했으므로 요청 세션에 밀린 변경이 없다. `day`는 `today_kst()`. 가짜 모드는 세지 않는다. 지난 날짜 행은 지우지 않는다(하루 한 행이라 양이 작다).

## 사진 저장소

```python
class Storage(ABC):
    kind: str                      # "s3" | "local"
    def put(key, data) -> None
    def get(key) -> bytes
    def url(key, photo_id) -> str  # API 응답의 사진 url
```

- `S3Storage(bucket, region, expires, client=None)`: `boto3.client("s3", region_name=..., config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))`. `put_object(Bucket, Key, Body, ContentType="image/jpeg")`(ACL 없음), `get_object`, `generate_presigned_url("get_object", Params={"Bucket", "Key"}, ExpiresIn=expires)`. `ClientError`/`BotoCoreError`는 `502 storage_unavailable`로 바꾸고 `type(exc).__name__`만 로그에 남긴다. 자격 증명은 넘기지 않는다.
- `LocalStorage(root)`: 키를 `root` 아래 경로로 바꾸되 `root` 밖으로 나가면 거부한다. `url()`은 `/api/photos/{photo_id}/file`. 파일이 없으면 `404`, 그 밖의 `OSError`는 `502 storage_unavailable`.
- `get_storage()`: `(S3_BUCKET, AWS_REGION, PRESIGN_EXPIRES_SECONDS, UPLOAD_DIR)`가 같으면 같은 객체를 돌려준다(S3 클라이언트를 매번 만들지 않기 위해서). `storage_kind()`는 설정만 보고 `s3`/`local`을 돌려줘 `health`가 클라이언트를 만들지 않는다.
- 키: `photos/{yyyy}/{mm}/{photo_id}.jpg` (KST 기준 연·월). 사용자 입력 파일명을 쓰지 않는다.
- `GET /api/photos/{photo_id}/file`: `LocalStorage`일 때만 JPEG를 돌려준다(기기 ID를 검사하지 않는 것은 그대로. `<img>`가 헤더를 못 보낸다). `S3Storage`이거나 행이 없거나 파일 없는 자리표시 사진이면 `404`.
- 같은 장면에 다시 올리면 장면 상태가 새 사진을 가리킨다. 이전 사진의 행과 객체는 지우지 않는다(분석 사진은 여러 건이 같이 쓰고, 삭제 권한이 IAM 역할에 필요해진다). 정리는 후속 일이다.

## 서비스 변경

- 라우터가 `SessionDep`를 받아 `mock/service.py`, `services/assist.py`에 `session`을 넘긴다.
- `mock/service.py`의 `get_*_record`, `create_*`, `patch_report`, `list_reports`, `report_out`, `guide_out` 등은 `session`을 받아 DB를 쓴다. 가짜/실제 모드가 같이 쓰는 로직이라 두 모드가 같은 테이블을 쓴다.
- 쓰는 함수는 마지막에 `session.commit()`을 한다. AI 호출이 실패하면 아무것도 쓰지 않는다(분석과 사진은 호출이 성공한 뒤에만 저장).
- 사진 URL은 응답을 만들 때 `store.photo_url(photo)`로 만든다. 레코드는 사진 ID만 가진다.
- 사전 점검은 `photos` 행을 기기 ID로 찾은 뒤 저장소에서 바이트를 읽고, 그 뒤에 호출 수를 센다(저장소 오류로 호출 수가 줄지 않게).

## 배포 파일

- `Dockerfile`: 바꾸지 않는다. `/app/uploads`는 이미 컨테이너 사용자(`app`) 소유다.
- `docker-compose.yml`: `S3_BUCKET`, `AWS_REGION`, `DATABASE_URL`은 이미 넘어간다. `S3_BUCKET` 없이 띄울 때 사진이 컨테이너 교체로 사라지지 않게 `uploads` 이름 있는 볼륨을 `/app/uploads`에 붙인다.
- 새 의존성은 없다(`sqlmodel`, `psycopg`, `boto3`는 이미 `pyproject.toml`에 있다).

## 테스트

- `conftest.py`: SQLite 메모리 엔진(`sqlite://`, `StaticPool`, `check_same_thread=False`)을 `db`에 끼우고 테이블을 만든다. 업로드 경로는 임시 폴더, `S3_BUCKET`은 비운다. 매 테스트마다 초기화한다.
- 기존 테스트의 기대값은 그대로 둔다. 저장소 내부(`store.photos`, `store.analyses`, `store.ai_usage`)를 직접 읽던 줄만 DB 도우미(`count_rows`, `set_photo_bytes`)로 바꾼다. `health` 응답에 `storage`가 늘어 한 줄의 기대값에 필드를 더한다.
- 새 테스트: 엔진을 새로 만든 뒤 조회, 다른 기기 404, 날짜별 호출 수, DB 연결 실패 503과 복구, `init_db` 재시도, 사진 대체, `S3Storage`(가짜 boto3), `LocalStorage` 경로 방어, 사진 파일 경로의 모드별 응답, 시각의 KST 오프셋.
