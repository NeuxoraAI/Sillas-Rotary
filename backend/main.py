import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers import auth, socioeconomico, tecnica, usuarios, regiones

# Serve the frontend — path is resolved relative to this file so it works
# both locally (uvicorn from backend/) and on Vercel (/var/task/backend/).
_FRONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "front")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
_STATIC_EXTENSIONS = (
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".webp",
    ".woff",
    ".woff2",
)


def _cache_control_for_path(path: str) -> str:
    if path.startswith("/api/"):
        return "no-store"
    if path.endswith(_STATIC_EXTENSIONS):
        return "public, max-age=3600"
    return "no-store"


def create_app() -> FastAPI:
    env = os.environ.get("ENV", "development").lower()
    docs_enabled = env != "production"

    app = FastAPI(
        title="Sillas Rotary API v2",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    @app.middleware("http")
    async def apply_security_headers(request: Request, call_next):
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        response.headers.setdefault("Cache-Control", _cache_control_for_path(request.url.path))
        return response

    app.include_router(auth.router, prefix="/api")
    app.include_router(socioeconomico.router, prefix="/api")
    app.include_router(tecnica.router, prefix="/api")
    app.include_router(usuarios.router, prefix="/api")
    app.include_router(regiones.router, prefix="/api")

    @app.get("/api/health")
    def health() -> JSONResponse:
        return JSONResponse(content={"status": "ok"})


    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/login.html")


    app.mount("/", StaticFiles(directory=_FRONT_DIR, html=True), name="frontend")
    return app


app = create_app()
