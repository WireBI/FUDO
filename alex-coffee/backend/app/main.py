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

# Create a list of allowed origins
origins = [
    settings.frontend_url,
    "https://fudo-theta.vercel.app",
    "http://localhost:3000",
    "http://localhost:3001",
]

# Ensure the frontend_url doesn't have a trailing slash which can sometimes cause issues in origin matching
if settings.frontend_url and settings.frontend_url.endswith("/"):
    origins.append(settings.frontend_url[:-1])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(sync.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    from fastapi.responses import JSONResponse
    status_code = 500
    detail = str(exc)
    
    if hasattr(exc, "status_code"):
        status_code = exc.status_code
    if hasattr(exc, "detail"):
        detail = exc.detail
    
    # Log full traceback to console
    print(f"ERROR: {detail}")
    traceback.print_exc()
        
    response = JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "traceback": traceback.format_exc(),
            "type": type(exc).__name__,
            "path": request.url.path
        },
    )
    # Manually add CORS headers to error responses
    origin = request.headers.get("origin")
    if origin in origins or "*" in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Also handle FastAPI's built-in RequestValidationError to avoid CORS issues on bad requests
@app.exception_handler(422)
async def validation_exception_handler(request, exc):
    return await global_exception_handler(request, exc)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "alex-coffee-analytics"}
