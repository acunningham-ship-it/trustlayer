"""TrustLayer Backend - Universal AI Trust Layer API"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import connectors, verify, learn, costs, compare, knowledge, workflows, settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])


@app.get("/")
async def root():
    return {"name": "TrustLayer", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
