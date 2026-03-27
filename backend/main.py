import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import init_db
from routers import auth, socioeconomico, tecnica

os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="Sillas Rotary API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(socioeconomico.router, prefix="/api")
app.include_router(tecnica.router, prefix="/api")


@app.on_event("startup")
def startup_event() -> None:
    init_db.init()


@app.get("/")
def root() -> dict:
    return {"status": "ok", "sistema": "Sillas Rotary API"}
