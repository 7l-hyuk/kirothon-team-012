# 1단계: 프론트 빌드. frontend/package.json이 없으면 빈 dist만 만듭니다(프론트는 따로 추가).
FROM node:24-slim AS frontend
WORKDIR /src
COPY . .
RUN if [ -f frontend/package.json ]; then \
      cd frontend && npm ci && npm run build; \
    else \
      mkdir -p frontend/dist; \
    fi

# 2단계: 백엔드 이미지. 프론트 빌드 결과물을 /app/static 으로 복사해 FastAPI가 서빙합니다.
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir uv

WORKDIR /app
# uv.lock에 잠긴 버전만 설치합니다(--frozen). 잠금 파일은 갱신하지 않습니다.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY backend/data ./data
COPY --from=frontend /src/frontend/dist /app/static

# root가 아닌 사용자로 실행합니다. uploads는 S3_BUCKET이 없을 때만 씁니다.
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /app/uploads \
    && chown app:app /app/uploads
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
