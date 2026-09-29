"""
Havi - Consent Verification Service.
Authorization layer: "Is there a verifiable record that this person consented to this usage?"

Consent verification based on cryptographically signed consent records
and declared usage permissions.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db_models import ConsentRecord
from ..utils.crypto import generate_consent_id, hash_consent_record


def create_consent(
    db: Session,
    speaker_id: str,
    voice_id: str,
    person_name: str,
    purpose: str,
    permitted_usage: list[str],
    expires_days: int = 365
) -> dict:
    """Create a new consent record with cryptographic integrity hash."""
    consent_id = generate_consent_id()
    now = datetime.utcnow()
    expires_at = now + timedelta(days=expires_days)

    consent_data = {
        "consent_id": consent_id,
        "speaker_id": speaker_id,
        "voice_id": voice_id,
        "person_name": person_name,
        "purpose": purpose if isinstance(purpose, str) else purpose.value,
        "permitted_usage": permitted_usage,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "status": "ACTIVE",
    }

    record_hash = hash_consent_record(consent_data)

    record = ConsentRecord(
        consent_id=consent_id,
        speaker_id=speaker_id,
        voice_id=voice_id,
        person_name=person_name,
        purpose=purpose if isinstance(purpose, str) else purpose.value,
        permitted_usage=permitted_usage,
        created_at=now,
        expires_at=expires_at,
        status="ACTIVE",
        record_hash=record_hash,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return _serialize_consent(record)


def verify_consent(
    db: Session,
    speaker_id: str,
    claimed_purpose: Optional[str] = None
) -> dict:
    """Check if a valid consent record exists for a speaker and purpose."""
    consents = db.query(ConsentRecord).filter(
        ConsentRecord.speaker_id == speaker_id
    ).all()

    if not consents:
        return {
            "consent_found": False,
            "consent_status": "NOT_FOUND",
            "purpose_match": False,
            "usage_authorized": False,
            "consent_id": None,
            "details": "No consent record found for this speaker",
        }

    now = datetime.utcnow()
    active = [c for c in consents if c.status == "ACTIVE" and c.expires_at > now]

    if not active:
        latest = max(consents, key=lambda c: c.created_at)
        status = "EXPIRED" if latest.status == "ACTIVE" else latest.status
        return {
            "consent_found": True,
            "consent_status": status,
            "purpose_match": False,
            "usage_authorized": False,
            "consent_id": latest.consent_id,
            "details": f"Consent record found but {status.lower()}",
        }

    if claimed_purpose:
        matching = [
            c for c in active
            if (c.purpose.lower() == claimed_purpose.lower() or
                claimed_purpose.lower() in [u.lower() for u in (c.permitted_usage or [])])
        ]

        if matching:
            consent = matching[0]
            integrity = _verify_integrity(consent)
            return {
                "consent_found": True,
                "consent_status": "ACTIVE",
                "purpose_match": True,
                "usage_authorized": integrity,
                "consent_id": consent.consent_id,
                "details": f"Active consent verified. Purpose: {consent.purpose}. "
                          f"Integrity: {'verified' if integrity else 'COMPROMISED'}",
            }
        else:
            consent = active[0]
            return {
                "consent_found": True,
                "consent_status": "ACTIVE",
                "purpose_match": False,
                "usage_authorized": False,
                "consent_id": consent.consent_id,
                "details": f"Consent exists for '{consent.purpose}' but "
                          f"claimed purpose '{claimed_purpose}' does not match",
            }

    consent = active[0]
    return {
        "consent_found": True,
        "consent_status": "ACTIVE",
        "purpose_match": True,
        "usage_authorized": True,
        "consent_id": consent.consent_id,
        "details": f"Active consent found. Purpose: {consent.purpose}",
    }


def revoke_consent(db: Session, consent_id: str) -> dict:
    record = db.query(ConsentRecord).filter(ConsentRecord.consent_id == consent_id).first()
    if not record:
        raise ValueError(f"Consent {consent_id} not found")
    record.status = "REVOKED"
    record.revoked_at = datetime.utcnow()
    db.commit()
    return {"consent_id": consent_id, "status": "REVOKED"}


def get_consent(db: Session, consent_id: str) -> Optional[dict]:
    record = db.query(ConsentRecord).filter(ConsentRecord.consent_id == consent_id).first()
    return _serialize_consent(record) if record else None


def get_all_consents(db: Session) -> list[dict]:
    records = db.query(ConsentRecord).order_by(ConsentRecord.created_at.desc()).all()
    return [_serialize_consent(r) for r in records]


def get_active_consents_count(db: Session) -> int:
    now = datetime.utcnow()
    return db.query(ConsentRecord).filter(
        ConsentRecord.status == "ACTIVE",
        ConsentRecord.expires_at > now,
    ).count()


def get_consents_for_speaker(db: Session, speaker_id: str) -> list[dict]:
    records = db.query(ConsentRecord).filter(
        ConsentRecord.speaker_id == speaker_id
    ).order_by(ConsentRecord.created_at.desc()).all()
    return [_serialize_consent(r) for r in records]


def _verify_integrity(record: ConsentRecord) -> bool:
    """Verify the cryptographic integrity of a consent record."""
    check_data = {
        "consent_id": record.consent_id,
        "speaker_id": record.speaker_id,
        "voice_id": record.voice_id,
        "person_name": record.person_name,
        "purpose": record.purpose,
        "permitted_usage": record.permitted_usage or [],
        "created_at": record.created_at.isoformat(),
        "expires_at": record.expires_at.isoformat(),
        "status": "ACTIVE",  # Hash was computed at creation when status was ACTIVE
    }
    return hash_consent_record(check_data) == record.record_hash


def _serialize_consent(record: ConsentRecord) -> dict:
    return {
        "consent_id": record.consent_id,
        "speaker_id": record.speaker_id,
        "voice_id": record.voice_id,
        "person_name": record.person_name,
        "purpose": record.purpose,
        "permitted_usage": record.permitted_usage or [],
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        "status": record.status,
        "record_hash": record.record_hash,
    }
