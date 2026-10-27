from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # v1 convenience: create tables on boot. Replace with Alembic for prod.
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Allow a local frontend (Next.js etc.) to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs"}
