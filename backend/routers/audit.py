"""Audit Log — placeholder for v0.2 agent activity tracking."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/events")
async def list_events():
    """List audit events (placeholder — returns empty list)."""
    return []


@router.get("/status")
async def audit_status():
    """Get audit log status."""
    return {"active": False, "message": "Audit log coming in v0.2"}
