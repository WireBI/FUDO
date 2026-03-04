from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import dashboard, sync, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    from app.database import init_db
    await init_db()
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
