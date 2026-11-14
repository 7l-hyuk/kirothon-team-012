# 배포

`main`에 push하면 GitHub Actions(`.github/workflows/deploy.yml`)가 EC2에서 `deploy/deploy.sh`를 실행합니다.

```
main push → GitHub Actions → (OIDC로 AWS 임시 권한) → SSM 명령 → EC2: deploy/deploy.sh
사용자 ──HTTPS──> CloudFront ──HTTP──> EC2 (Docker Compose: app + db) ──> S3, Claude API
```

## 구성 요소

| 항목 | 값 |
|---|---|
| 리전 | `ap-northeast-2` |
| 서버 | EC2 `t3.small`, Amazon Linux 2023, Docker Compose |
| 서버 경로 | 코드 `/opt/shingomate/repo`, 환경변수 `/opt/shingomate/.env` |
| 사진 저장 | S3 비공개 버킷 (EC2의 IAM 역할로 접근) |
| HTTPS | CloudFront 기본 도메인 |
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
