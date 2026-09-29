"""
Havi - Consent Management Router.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import consent as consent_service
from ..services import speaker, audit
from ..models.schemas import ConsentCreateRequest

router = APIRouter(prefix="/api/consent", tags=["Consent"])


@router.post("")
async def create_consent(request: ConsentCreateRequest, db: Session = Depends(get_db)):
    """Create a consent record for a registered speaker."""
    spk = speaker.get_speaker(db, request.speaker_id)
    if not spk:
        raise HTTPException(status_code=404, detail="Speaker not found")

    result = consent_service.create_consent(
        db,
        speaker_id=request.speaker_id,
        voice_id=spk["voice_id"],
        person_name=spk["name"],
        purpose=request.purpose.value if hasattr(request.purpose, 'value') else request.purpose,
        permitted_usage=request.permitted_usage,
        expires_days=request.expires_days,
    )

    audit.log_event(db, "CONSENT_CREATED", {
        "consent_id": result["consent_id"],
        "speaker_id": request.speaker_id,
        "purpose": request.purpose.value if hasattr(request.purpose, 'value') else request.purpose,
    })

    return result


@router.get("")
async def list_consents(db: Session = Depends(get_db)):
    consents = consent_service.get_all_consents(db)
    return {"consents": consents, "total": len(consents)}


@router.get("/{consent_id}")
async def get_consent(consent_id: str, db: Session = Depends(get_db)):
    record = consent_service.get_consent(db, consent_id)
    if not record:
        raise HTTPException(status_code=404, detail="Consent record not found")
    return record


@router.delete("/{consent_id}")
async def revoke_consent(consent_id: str, db: Session = Depends(get_db)):
    try:
        result = consent_service.revoke_consent(db, consent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    audit.log_event(db, "CONSENT_REVOKED", {"consent_id": consent_id})
    return result


@router.get("/speaker/{speaker_id}")
async def get_speaker_consents(speaker_id: str, db: Session = Depends(get_db)):
    consents = consent_service.get_consents_for_speaker(db, speaker_id)
    return {"consents": consents, "total": len(consents)}
