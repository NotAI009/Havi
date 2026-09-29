"""
Havi - Audit Trail Router.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import audit as audit_service

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("")
async def get_audit_trail(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Get the audit trail with chain integrity verification."""
    return audit_service.get_audit_trail(db, limit=limit, offset=offset)


@router.get("/verify")
async def verify_chain(db: Session = Depends(get_db)):
    """Verify the integrity of the entire audit chain."""
    is_valid = audit_service.verify_full_chain(db)
    return {
        "chain_valid": is_valid,
        "message": "Audit chain integrity verified" if is_valid else "CHAIN INTEGRITY COMPROMISED"
    }


@router.get("/report/{report_id}")
async def get_report_events(report_id: str, db: Session = Depends(get_db)):
    events = audit_service.get_events_for_report(db, report_id)
    return {"events": events, "total": len(events)}


@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """Get analytics data for dashboard charts."""
    return {
        "event_counts": audit_service.get_event_counts_by_type(db),
        "daily_activity": audit_service.get_daily_activity(db),
    }
