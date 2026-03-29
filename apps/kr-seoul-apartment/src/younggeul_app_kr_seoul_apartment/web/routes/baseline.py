from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/baseline", tags=["baseline"])


@router.post("")
async def run_baseline() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented (#74b)")
