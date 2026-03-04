from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import dashboard, sync, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Don't initialize DB on startup - let it happen lazily on first request
    # This avoids SQLAlchemy trying to create a sync engine which imports psycopg2
    yield


app = FastAPI(
    title="Alex Coffee Analytics",
    description="Analytics dashboard powered by FU.DO POS data",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(sync.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "alex-coffee-analytics"}
