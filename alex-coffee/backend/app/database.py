from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import sys

from app.config import settings

# Lazy initialization - prevent psycopg2 import error on module load
_engine = None
_async_session = None
_db_initialized = False


def _create_engine_safe():
    """Create async engine with fallback for missing psycopg2"""
    url = settings.database_url
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Normalize DATABASE_URL for asyncpg
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Robustly strip ALL query parameters (like ?sslmode=... or &channel_binding=...)
    # asyncpg often fails if standard postgres query params are passed to it
    if "?" in url:
        url = url.split("?")[0]

    # Inject a fake psycopg2 module to prevent import errors
    # SQLAlchemy checks for psycopg2 even when using asyncpg
    if "psycopg2" not in sys.modules:
        import types
        # Create fake psycopg2 module
        p2 = types.ModuleType("psycopg2")
        p2.__version__ = "2.9.0"
        p2.paramstyle = "pyformat"
        sys.modules["psycopg2"] = p2

        # Create fake psycopg2.extensions
        ext = types.ModuleType("psycopg2.extensions")
        sys.modules["psycopg2.extensions"] = ext
        p2.extensions = ext

        # Create fake psycopg2.extras (fixes "cannot import name 'extras' from '<unknown module name>'")
        ex = types.ModuleType("psycopg2.extras")
        sys.modules["psycopg2.extras"] = ex
        p2.extras = ex

    try:
        engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=False,
            connect_args={"timeout": 10}
        )
        return engine
    except Exception as e:
        raise ValueError(
            f"SQLAlchemy failed to initialize async engine: {e}. "
            "Ensure DATABASE_URL is set correctly."
        )


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_safe()
    return _engine


def get_session_factory():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _async_session


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency for getting a database session"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def init_db():
    """Initialize database tables (call once on first DB request)"""
    global _db_initialized
    if _db_initialized:
        return

    try:
        engine = get_engine()
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.run_sync(Base.metadata.create_all)
            
            # Patch: Ensure fudo_api_id column exists
            try:
                # PostgreSQL style
                await conn.execute(text("ALTER TABLE api_credentials ADD COLUMN IF NOT EXISTS fudo_api_id VARCHAR;"))
            except Exception:
                try:
                    # SQLite style (doesn't support IF NOT EXISTS, so try adding directly)
                    await conn.execute(text("ALTER TABLE api_credentials ADD COLUMN fudo_api_id VARCHAR;"))
                except Exception:
                    # Column likely already exists
                    pass
        _db_initialized = True
    except Exception as e:
        # Log but don't fail - tables might already exist
        print(f"Note: Could not initialize database on first run: {e}")
        _db_initialized = True


