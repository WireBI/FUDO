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

    # Inject a fake psycopg2 module to prevent import errors
    # SQLAlchemy checks for psycopg2 even when using asyncpg
    if "psycopg2" not in sys.modules:
        class FakePsycopg2:
            __version__ = "2.9.0"
            paramstyle = "pyformat"
        sys.modules["psycopg2"] = FakePsycopg2()
        sys.modules["psycopg2.extensions"] = type(sys)("psycopg2.extensions")

    try:
        engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=False,
            connect_args={"timeout": 10}
        )
        return engine
    except ModuleNotFoundError as e:
        if "psycopg2" in str(e):
            # If psycopg2 still fails, it's a deep SQLAlchemy issue
            raise ValueError(
                f"SQLAlchemy failed to initialize async engine: {e}. "
                "Ensure DATABASE_URL is set correctly with postgresql+asyncpg:// protocol."
            )
        raise


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
            await conn.run_sync(Base.metadata.create_all)
        _db_initialized = True
    except Exception as e:
        # Log but don't fail - tables might already exist
        print(f"Note: Could not initialize database on first run: {e}")
        _db_initialized = True


