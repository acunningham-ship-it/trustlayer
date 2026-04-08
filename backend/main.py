"""TrustLayer Backend - Universal AI Trust Layer API"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .database import init_db
from .routers import connectors, verify, learn, costs, compare, knowledge, workflows, settings, history, router, consistency

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RemoveTrailingSlashMiddleware(BaseHTTPMiddleware):
    """Normalize URLs by removing trailing slashes and re-routing.

    This ensures both /api/verify and /api/verify/ work without 307 redirects.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/" and request.url.path.endswith("/"):
            new_path = request.url.path.rstrip("/")
            request.scope["path"] = new_path
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="TrustLayer API",
    description="The universal AI trust layer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RemoveTrailingSlashMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connectors.router, prefix="/api/connectors", tags=["connectors"])
app.include_router(verify.router, prefix="/api/verify", tags=["verify"])
app.include_router(learn.router, prefix="/api/learn", tags=["learn"])
app.include_router(costs.router, prefix="/api/costs", tags=["costs"])
app.include_router(compare.router, prefix="/api/compare", tags=["compare"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(router.router, prefix="/api/router", tags=["router"])
app.include_router(consistency.router, prefix="/api/consistency", tags=["consistency"])


@app.get("/")
async def root():
    return {"name": "TrustLayer", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/info")
async def info():
    """Get app info (version and data directory)."""
    return {
        "version": "0.1.0",
        "dataDir": os.path.expanduser("~/.trustlayer")
    }
