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

# Allowed browser origins come from CORS_ORIGINS (comma-separated). Defaults to
# localhost for dev; set it to your deployed frontend URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs"}
