"""신고메이트 FastAPI 앱. ANTHROPIC_API_KEY가 없으면 가짜(mock) 응답, 있으면 Claude를 호출합니다."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from app import db
from app.config import get_settings, is_mock
from app.errors import ApiError, ErrorCode, register_error_handlers
from app.routers import analyses, assets, photos, procedures, reports
from app.services import procedures as procedure_data


def create_app(static_dir: str | Path | None = None) -> FastAPI:
    static_root = Path(static_dir or get_settings().static_dir)
    procedure_data.load_procedures()  # 절차 데이터 형식이 틀리면 여기서 시작을 멈춥니다.

    app = FastAPI(title="신고메이트 API", version="0.2.0")
    register_error_handlers(app)

    @app.middleware("http")
    async def add_mock_header(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api") and is_mock():  # 가짜로 응답했을 때만 붙입니다.
            response.headers["X-Mock"] = "true"
        return response

    app.include_router(analyses.router)
    app.include_router(reports.router)
    app.include_router(procedures.router)
    app.include_router(photos.router)
    app.include_router(assets.router)

    @app.get("/api/health")
    def health() -> dict[str, str | bool]:
        # DB가 죽어 있어도 200입니다. 배포 스크립트의 상태 확인이 DB 때문에 막히지 않게 합니다.
        return {"status": "ok", "db": "ok" if db.check_db() else "unavailable", "mock": is_mock()}

    if (static_root / "index.html").is_file():
        root = static_root.resolve()

        # React 빌드 결과물 서빙. /api 아래 알 수 없는 경로는 index.html이 아니라 404 JSON입니다.
        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str) -> FileResponse:
            if full_path == "api" or full_path.startswith("api/"):
                raise ApiError(404, ErrorCode.NOT_FOUND, "찾을 수 없어요. 주소를 다시 확인해 주세요.")
            candidate = (root / full_path).resolve()
            if full_path and candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
            return FileResponse(root / "index.html")

    else:

        @app.get("/", include_in_schema=False)
        async def index() -> dict[str, str]:
            return {"service": "shingomate", "docs": "/docs"}

    return app


app = create_app()
