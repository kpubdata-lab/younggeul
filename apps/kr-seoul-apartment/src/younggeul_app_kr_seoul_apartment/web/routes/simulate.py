from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/simulate", tags=["simulate"])


@router.post("")
async def create_simulation_run() -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented (#74b)")


@router.get("/{run_id}")
async def get_simulation_run(run_id: str) -> None:
    _ = run_id
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented (#74b)")
