"""Admin section for managing API credentials."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.config import settings
from app.database import get_db
from app.models import APICredential

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CredentialUpdate(BaseModel):
    fudo_api_id: str | None = None
    fudo_api_secret: str


class CredentialResponse(BaseModel):
    id: int
    fudo_api_id: str | None
    fudo_api_secret_masked: str  # Never return the actual secret
    updated_at: datetime
    updated_by: str | None


async def verify_admin_key(x_admin_key: str = Header(None)):
    """Verify the admin API key from request header."""
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")
    return x_admin_key


@router.get("/credentials", response_model=CredentialResponse | None)
async def get_credentials(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    """Get current FU.DO API credentials (masked)."""
    result = await db.execute(
        select(APICredential).order_by(APICredential.updated_at.desc()).limit(1)
    )
    cred = result.scalars().first()

    if not cred:
        return None

    return CredentialResponse(
        id=cred.id,
        fudo_api_id=cred.fudo_api_id,
        fudo_api_secret_masked=f"...{cred.fudo_api_secret[-4:] if cred.fudo_api_secret else ''}",
        updated_at=cred.updated_at,
        updated_by=cred.updated_by,
    )


@router.post("/credentials")
async def update_credentials(
    update: CredentialUpdate,
    db: AsyncSession = Depends(get_db),
    admin_key: str = Depends(verify_admin_key),
):
    """Update FU.DO API credentials."""
    from app.encryption import get_encryption_manager

    secret = update.fudo_api_secret.strip()
    if not secret:
        raise HTTPException(status_code=400, detail="API secret cannot be empty")

    # Encrypt before storing
    encryption_manager = get_encryption_manager()
    encrypted_secret = encryption_manager.encrypt(secret)

    # Store new credential
    cred = APICredential(
        fudo_api_id=update.fudo_api_id.strip() if update.fudo_api_id else None,
        fudo_api_secret=encrypted_secret,
        updated_by="admin",
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)

    return {
        "status": "success",
        "message": "API credentials updated",
        "updated_at": cred.updated_at,
    }


@router.get("/credentials/status")
async def credentials_status(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_admin_key),
):
    """Check if credentials are configured."""
    result = await db.execute(
        select(APICredential).order_by(APICredential.updated_at.desc()).limit(1)
    )
    cred = result.scalars().first()

    if not cred:
        # Check if env var is set
        has_env_secret = bool(settings.fudo_api_secret)
        has_env_id = bool(settings.fudo_api_id)
        return {
            "configured": has_env_secret and has_env_id,
            "source": "environment" if has_env_secret or has_env_id else "none",
            "note": f"Using environment variables {'FUDO_API_ID ' if has_env_id else ''}{'FUDO_API_SECRET' if has_env_secret else ''}"
            if has_env_secret or has_env_id
            else "No credentials configured",
        }

    return {
        "configured": True,
        "source": "database",
        "updated_at": cred.updated_at.isoformat(),
        "updated_by": cred.updated_by,
        "note": "Using credentials from database (encrypted)",
    }
