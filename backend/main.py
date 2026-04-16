from fastapi import FastAPI

from routers import auth, socioeconomico, tecnica

app = FastAPI(title="Sillas Rotary API")

app.include_router(auth.router, prefix="/api")
app.include_router(socioeconomico.router, prefix="/api")
app.include_router(tecnica.router, prefix="/api")
