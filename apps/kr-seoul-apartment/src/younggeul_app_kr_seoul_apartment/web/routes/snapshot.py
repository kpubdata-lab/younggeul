from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/snapshot", tags=["snapshot"])


@router.get("")
async def list_snapshots() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented (#74b)")


@router.post("/publish")
async def publish_snapshot_route() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented (#74b)")
