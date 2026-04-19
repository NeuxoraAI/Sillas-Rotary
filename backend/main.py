import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from routers import auth, socioeconomico, tecnica, usuarios, regiones

app = FastAPI(title="Sillas Rotary API v2")

app.include_router(auth.router, prefix="/api")
app.include_router(socioeconomico.router, prefix="/api")
app.include_router(tecnica.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(regiones.router, prefix="/api")

# Serve the frontend — path is resolved relative to this file so it works
# both locally (uvicorn from backend/) and on Vercel (/var/task/backend/).
_FRONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "front")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/login.html")


app.mount("/", StaticFiles(directory=_FRONT_DIR, html=True), name="frontend")
