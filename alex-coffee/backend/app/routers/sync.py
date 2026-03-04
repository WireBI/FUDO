from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.fudo_client import FudoClient
from app.models import SyncLog
from app.sync import run_full_sync

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("")
async def trigger_sync(
    days_back: int = Query(30, ge=1, le=1460, description="Days of sales history to sync"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a full data sync from FU.DO."""
    result = await run_full_sync(db, days_back=days_back)
    return result


@router.get("/status")
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Get the latest sync status."""
    result = await db.execute(
        select(SyncLog).order_by(SyncLog.started_at.desc()).limit(5)
    )
    logs = result.scalars().all()

    return {
        "recent_syncs": [
            {
                "id": log.id,
                "type": log.sync_type,
                "status": log.status,
                "records_synced": log.records_synced,
                "error": log.error_message,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            }
            for log in logs
        ]
    }


@router.get("/health")
async def fudo_health():
    """Check if the FU.DO API is reachable."""
    client = FudoClient()
    try:
        healthy = await client.health_check()
        return {"fudo_api": "connected" if healthy else "unreachable"}
    finally:
        await client.close()
