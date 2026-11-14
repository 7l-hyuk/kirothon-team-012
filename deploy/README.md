# 배포

PR에서는 `.github/workflows/ci.yml`이 백엔드 테스트, 프론트 빌드, Docker 이미지 빌드를 검사하고, `main`에 병합되면 GitHub Actions(`.github/workflows/deploy.yml`)가 EC2에서 `deploy/deploy.sh`를 실행해 배포합니다.

```
PR → ci.yml (backend / frontend / docker 검사)
main 병합 → GitHub Actions → (OIDC로 AWS 임시 권한) → SSM 명령 → EC2: deploy/deploy.sh
사용자 ──HTTPS──> CloudFront ──HTTP──> EC2 (Docker Compose: app + db) ──> S3, Claude API
```

## 구성 요소

| 항목 | 값 |
|---|---|
| 리전 | `ap-northeast-2` |
| 서버 | EC2 `t3.small`, Amazon Linux 2023, Docker Compose |
| 서버 경로 | 코드 `/opt/shingomate/repo`, 환경변수 `/opt/shingomate/.env` |
| 사진 저장 | S3 비공개 버킷 (EC2의 IAM 역할로 접근) |
| 서비스 주소 | `https://www.room2ate.cloud` (CloudFront 기본 주소 `https://d2b992irefoevf.cloudfront.net`도 동작) |
| HTTPS | CloudFront |
| 서버 접속 | SSM Session Manager (SSH 포트는 열지 않음) |

인스턴스 ID, 배포용 역할 ARN, 리전은 GitHub 레포의 Variables에 있습니다(`EC2_INSTANCE_ID`, `AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`). GitHub에는 비밀 값을 저장하지 않습니다.

## 배포 스크립트가 하는 일

1. `main`의 최신 코드를 받습니다.
2. `docker-compose.yml`이 없으면 여기서 끝냅니다.
3. `docker compose up -d --build`로 앱과 DB를 띄웁니다.
4. `http://localhost/api/health`가 2분 안에 응답하는지 확인합니다. 응답이 없으면 컨테이너 로그를 출력하고 실패 처리합니다.

## 서버 환경변수

비밀 값은 서버의 `/opt/shingomate/.env`에만 둡니다. 레포와 GitHub에는 넣지 않습니다. 처음 한 번 Session Manager로 접속해 만듭니다.

```bash
sudo tee /opt/shingomate/.env >/dev/null <<'ENV'
ANTHROPIC_API_KEY=발급받은_키
CLAUDE_MODEL=claude-opus-5-5
AI_DAILY_LIMIT=20
POSTGRES_USER=shingo
POSTGRES_PASSWORD=직접_정한_비밀번호
POSTGRES_DB=shingomate
DATABASE_URL=postgresql+psycopg://shingo:직접_정한_비밀번호@db:5432/shingomate
S3_BUCKET=버킷_이름
AWS_REGION=ap-northeast-2
PRESIGN_EXPIRES_SECONDS=3600
ENV
sudo chmod 600 /opt/shingomate/.env
```

## S3 버킷 CORS

접수 안내의 "사진 저장" 버튼은 화면의 스크립트가 S3 presigned URL에서 사진 파일을 받아 휴대폰 공유 시트로 넘깁니다. 이 요청은 서비스 도메인에서 S3 도메인으로 가므로 버킷에 CORS 규칙이 있어야 합니다. `<img>` 태그로 사진을 보여 주는 데는 필요하지 않습니다.

사진 버킷에 아래 규칙이 적용돼 있습니다. 레포의 코드로 관리되지 않는 AWS 설정이라, 버킷을 새로 만들면 다시 넣어야 합니다.

```json
{
  "CORSRules": [
    {
      "AllowedOrigins": [
        "https://www.room2ate.cloud",
        "https://d2b992irefoevf.cloudfront.net",
        "http://localhost:5173"
      ],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}
```

위 내용을 `cors.json`으로 저장한 뒤 적용하고 확인합니다.

```bash
aws s3api put-bucket-cors --bucket <버킷_이름> --cors-configuration file://cors.json
aws s3api get-bucket-cors --bucket <버킷_이름>
```

- 읽기(`GET`, `HEAD`)만 허용합니다. 업로드는 백엔드가 하므로 `PUT`은 열지 않습니다.
- 버킷의 공개 여부는 바뀌지 않습니다. 퍼블릭 액세스 차단은 그대로 켜 두고, 사진은 서명이 붙은 주소로만 열립니다.
- 서비스 주소가 바뀌거나 늘면 `AllowedOrigins`에 추가합니다.

## 수동 배포

Actions를 거치지 않고 서버에서 바로 실행할 수 있습니다.

```bash
sudo bash /opt/shingomate/repo/deploy/deploy.sh
```

## 문제 확인

```bash
cd /opt/shingomate/repo
sudo docker compose --env-file /opt/shingomate/.env ps
sudo docker compose --env-file /opt/shingomate/.env logs --tail 100 app
```

## 대회 종료 후 정리

리소스에는 모두 `Project=shingomate` 태그가 붙어 있습니다. EC2 인스턴스와 탄력적 IP를 지워야 비용이 더 나가지 않습니다.
