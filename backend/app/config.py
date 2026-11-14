"""환경변수 설정. 모든 값에 로컬 기본값이 있어 .env 없이도 뜹니다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 빈 값("")은 없는 것으로 보고 기본값을 씁니다. (compose가 빈 문자열을 넘기는 경우 대비)
    # .env 에 있는 POSTGRES_* 같은 다른 변수는 무시합니다.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_ignore_empty=True
    )

    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    ai_daily_limit: int = 20
    database_url: str = "postgresql+psycopg://shingo:shingo-local@localhost:5432/shingomate"
    s3_bucket: str | None = None
    aws_region: str = "ap-northeast-2"
    presign_expires_seconds: int = 3600
    upload_dir: str = "./uploads"
    static_dir: str = "/app/static"


@lru_cache
def get_settings() -> Settings:
    return Settings()
