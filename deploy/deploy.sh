#!/usr/bin/env bash
# EC2 서버에서 실행하는 배포 스크립트입니다.
# GitHub Actions가 SSM으로 호출하며, 서버에서 직접 실행해도 됩니다.
#   sudo bash /opt/shingomate/repo/deploy/deploy.sh
set -euo pipefail

APP_ROOT=/opt/shingomate
REPO_DIR="$APP_ROOT/repo"
ENV_FILE="$APP_ROOT/.env"
REPO_URL="${REPO_URL:-https://github.com/7l-hyuk/kirothon-team-012.git}"
BRANCH="${BRANCH:-main}"
HEALTH_URL="http://localhost/api/health"

echo "== 1. 코드 받기 ($BRANCH)"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"
git fetch --prune origin "$BRANCH"
git reset --hard "origin/$BRANCH"
echo "배포 커밋: $(git log -1 --format='%h %s')"

if [ ! -f docker-compose.yml ]; then
  echo "docker-compose.yml이 아직 없어서 컨테이너 실행은 건너뜁니다."
  exit 0
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "오류: $ENV_FILE 파일이 없습니다. deploy/README.md의 '서버 환경변수' 절을 보고 먼저 만들어 주세요." >&2
  exit 1
fi

echo "== 2. 빌드하고 실행"
docker compose --env-file "$ENV_FILE" up -d --build --remove-orphans

echo "== 3. 상태 확인"
for i in $(seq 1 30); do
  if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "정상 응답: $HEALTH_URL"
    docker compose --env-file "$ENV_FILE" ps
    docker image prune -f >/dev/null
    exit 0
  fi
  sleep 4
done

echo "오류: 2분 안에 $HEALTH_URL 이 응답하지 않았습니다." >&2
docker compose --env-file "$ENV_FILE" ps >&2
docker compose --env-file "$ENV_FILE" logs --tail 60 >&2
exit 1
