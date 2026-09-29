"""
Havi - Tamper-Evident Audit Trail Service.
Every verification event is cryptographically chained with SHA-256.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..db_models import AuditEntry
from ..utils.crypto import generate_event_id, hash_event, verify_chain


def log_event(
    db: Session,
    event_type: str,
    details: dict,
    report_id: Optional[str] = None,
) -> dict:
    """Add an event to the audit trail with cryptographic chaining."""
    event_id = generate_event_id()
    timestamp = datetime.utcnow()

    # Get previous hash for chaining
    last = db.query(AuditEntry).order_by(desc(AuditEntry.id)).first()
    previous_hash = last.entry_hash if last else ""

    event_data = {
        "event_id": event_id,
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "details": details,
        "previous_hash": previous_hash,
    }

    entry_hash = hash_event(event_data, previous_hash)

    entry = AuditEntry(
        event_id=event_id,
        timestamp=timestamp,
        event_type=event_type,
        details=details,
        report_id=report_id,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    db.add(entry)
    db.commit()

    return {
        "event_id": event_id,
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "details": details,
        "entry_hash": entry_hash,
    }


def get_audit_trail(db: Session, limit: int = 50, offset: int = 0) -> dict:
    total = db.query(AuditEntry).count()
    entries = db.query(AuditEntry).order_by(
        desc(AuditEntry.timestamp)
    ).offset(offset).limit(limit).all()

    return {
        "entries": [_serialize(e) for e in entries],
        "chain_valid": verify_full_chain(db),
        "total": total,
    }


def get_events_for_report(db: Session, report_id: str) -> list[dict]:
    entries = db.query(AuditEntry).filter(
        AuditEntry.report_id == report_id
    ).order_by(AuditEntry.timestamp).all()
    return [_serialize(e) for e in entries]


def verify_full_chain(db: Session) -> bool:
    """Verify the entire audit chain for tampering."""
    entries = db.query(AuditEntry).order_by(AuditEntry.id).all()
    if not entries:
        return True

    chain = []
    for e in entries:
        chain.append({
            "event_id": e.event_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            "event_type": e.event_type,
            "details": e.details or {},
            "previous_hash": e.previous_hash or "",
            "entry_hash": e.entry_hash,
        })
    return verify_chain(chain)


def get_suspicious_count(db: Session) -> int:
    return db.query(AuditEntry).filter(AuditEntry.event_type == "ALERT_GENERATED").count()


def get_verified_count(db: Session) -> int:
    return db.query(AuditEntry).filter(AuditEntry.event_type == "SPEAKER_VERIFIED").count()


def get_recent_verifications(db: Session, limit: int = 10) -> list[dict]:
    entries = db.query(AuditEntry).filter(
        AuditEntry.event_type.in_(["RISK_ENGINE", "SPEAKER_VERIFIED"])
    ).order_by(desc(AuditEntry.timestamp)).limit(limit).all()
    return [_serialize(e) for e in entries]


def get_event_counts_by_type(db: Session) -> dict:
    """Get event counts grouped by type for analytics."""
    results = db.query(
        AuditEntry.event_type, func.count(AuditEntry.id)
    ).group_by(AuditEntry.event_type).all()
    return {event_type: count for event_type, count in results}


def get_daily_activity(db: Session, days: int = 30) -> list[dict]:
    """Get daily verification activity for charts."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    entries = db.query(AuditEntry).filter(
        AuditEntry.timestamp >= cutoff,
        AuditEntry.event_type == "RISK_ENGINE"
    ).order_by(AuditEntry.timestamp).all()

    # Group by date
    daily = {}
    for e in entries:
        date_key = e.timestamp.strftime("%Y-%m-%d")
        if date_key not in daily:
            daily[date_key] = {"date": date_key, "verifications": 0, "alerts": 0}
        daily[date_key]["verifications"] += 1
        risk = (e.details or {}).get("risk_level", "")
        if risk == "HIGH":
            daily[date_key]["alerts"] += 1

    return list(daily.values())


def _serialize(e: AuditEntry) -> dict:
    return {
        "event_id": e.event_id,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "event_type": e.event_type,
        "details": e.details or {},
        "report_id": e.report_id,
        "previous_hash": e.previous_hash,
        "entry_hash": e.entry_hash,
    }
