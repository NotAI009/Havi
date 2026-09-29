"""
Havi - Voice Verification Router.
Full pipeline: audio upload → three verification layers → risk report → audit trail.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import VerificationReport
from ..services import speaker, deepfake, consent, risk_engine, audit
from ..utils.audio import preprocess_audio, compute_audio_hash, validate_audio, get_audio_duration
from ..utils.crypto import generate_report_id, hash_consent_record

router = APIRouter(prefix="/api/verify", tags=["Verification"])


@router.post("")
async def verify_voice(
    audio: UploadFile = File(...),
    claimed_speaker_id: Optional[str] = Form(None),
    claimed_purpose: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Full voice verification pipeline."""
    report_id = generate_report_id()
    audio_bytes = await audio.read()
    filename = audio.filename or "unknown.wav"
    audio_hash = compute_audio_hash(audio_bytes)

    audit.log_event(db, "VOICE_UPLOADED", {
        "filename": filename,
        "file_size": len(audio_bytes),
        "audio_hash": audio_hash[:16],
        "claimed_speaker_id": claimed_speaker_id,
    }, report_id=report_id)

    validation = validate_audio(audio_bytes)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])

    waveform, sr = preprocess_audio(audio_bytes)
    duration = get_audio_duration(waveform, sr)

    # Layer 1: Speaker Verification
    speaker_result = speaker.verify_speaker(
        db, waveform, sr, claimed_speaker_id=claimed_speaker_id
    )
    audit.log_event(db, "SPEAKER_VERIFIED", {
        "similarity": speaker_result["similarity_score"],
        "matched": speaker_result["matched"],
        "matched_speaker": speaker_result.get("matched_speaker_name"),
    }, report_id=report_id)

    # Layer 2: Deepfake Detection
    deepfake_result = deepfake.detect_deepfake(waveform, sr)
    audit.log_event(db, "SPOOF_ANALYSIS", {
        "synthetic_probability": deepfake_result["synthetic_probability"],
        "is_synthetic": deepfake_result["is_synthetic"],
        "indicators_count": len(deepfake_result["indicators"]),
    }, report_id=report_id)

    # Layer 3: Consent Verification
    target_speaker_id = claimed_speaker_id or speaker_result.get("matched_speaker_id")
    if target_speaker_id:
        consent_result = consent.verify_consent(db, target_speaker_id, claimed_purpose)
    else:
        consent_result = {
            "consent_found": False, "consent_status": "NOT_FOUND",
            "purpose_match": False, "usage_authorized": False,
            "consent_id": None, "details": "No speaker identified for consent check",
        }
    audit.log_event(db, "CONSENT_CHECK", {
        "consent_found": consent_result["consent_found"],
        "consent_status": consent_result["consent_status"],
        "purpose_match": consent_result["purpose_match"],
    }, report_id=report_id)

    # Risk Engine
    risk_result = risk_engine.compute_risk(
        speaker_similarity=speaker_result["similarity_score"],
        synthetic_probability=deepfake_result["synthetic_probability"],
        consent_found=consent_result["consent_found"],
        consent_status=consent_result["consent_status"],
        purpose_match=consent_result["purpose_match"],
        usage_authorized=consent_result["usage_authorized"],
    )
    audit.log_event(db, "RISK_ENGINE", {
        "risk_level": risk_result["risk_level"],
        "risk_score": risk_result["risk_score"],
        "filename": filename,
    }, report_id=report_id)

    if risk_result["risk_level"] == "HIGH":
        audit.log_event(db, "ALERT_GENERATED", {
            "risk_level": risk_result["risk_level"],
            "risk_score": risk_result["risk_score"],
            "filename": filename,
        }, report_id=report_id)

    # Persist report
    report_hash = hash_consent_record({
        "report_id": report_id,
        "speaker": speaker_result,
        "deepfake": deepfake_result,
        "consent": consent_result,
        "risk": risk_result,
    })

    db_report = VerificationReport(
        report_id=report_id,
        filename=filename,
        audio_hash=audio_hash,
        file_size=len(audio_bytes),
        duration=duration,
        speaker_similarity=speaker_result["similarity_score"],
        speaker_matched=speaker_result["matched"],
        matched_speaker_id=speaker_result.get("matched_speaker_id"),
        matched_speaker_name=speaker_result.get("matched_speaker_name"),
        synthetic_probability=deepfake_result["synthetic_probability"],
        is_synthetic=deepfake_result["is_synthetic"],
        deepfake_confidence=deepfake_result["confidence"],
        deepfake_indicators=deepfake_result["indicators"],
        consent_found=consent_result["consent_found"],
        consent_status=consent_result["consent_status"],
        purpose_match=consent_result["purpose_match"],
        usage_authorized=consent_result["usage_authorized"],
        consent_id=consent_result.get("consent_id"),
        risk_level=risk_result["risk_level"],
        risk_score=risk_result["risk_score"],
        risk_components=risk_result["components"],
        risk_reasons=risk_result["reasons"],
        report_hash=report_hash,
    )
    db.add(db_report)
    db.commit()

    return {
        "report_id": report_id,
        "timestamp": datetime.utcnow().isoformat(),
        "filename": filename,
        "duration": round(duration, 2),
        "speaker_verification": speaker_result,
        "deepfake_detection": deepfake_result,
        "consent_verification": consent_result,
        "risk_assessment": risk_result,
        "report_hash": report_hash,
    }


@router.get("/reports")
async def list_reports(limit: int = 20, db: Session = Depends(get_db)):
    """List recent verification reports."""
    from sqlalchemy import desc
    reports = db.query(VerificationReport).order_by(
        desc(VerificationReport.created_at)
    ).limit(limit).all()

    return {
        "reports": [
            {
                "report_id": r.report_id,
                "filename": r.filename,
                "risk_level": r.risk_level,
                "risk_score": r.risk_score,
                "speaker_similarity": r.speaker_similarity,
                "synthetic_probability": r.synthetic_probability,
                "consent_status": r.consent_status,
                "matched_speaker_name": r.matched_speaker_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
        "total": len(reports),
    }


@router.get("/reports/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    """Get a specific verification report with its audit trail."""
    r = db.query(VerificationReport).filter(
        VerificationReport.report_id == report_id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")

    events = audit.get_events_for_report(db, report_id)

    return {
        "report_id": r.report_id,
        "filename": r.filename,
        "duration": r.duration,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "speaker_verification": {
            "matched": r.speaker_matched,
            "similarity_score": r.speaker_similarity,
            "matched_speaker_id": r.matched_speaker_id,
            "matched_speaker_name": r.matched_speaker_name,
        },
        "deepfake_detection": {
            "is_synthetic": r.is_synthetic,
            "synthetic_probability": r.synthetic_probability,
            "confidence": r.deepfake_confidence,
            "indicators": r.deepfake_indicators or [],
        },
        "consent_verification": {
            "consent_found": r.consent_found,
            "consent_status": r.consent_status,
            "purpose_match": r.purpose_match,
            "usage_authorized": r.usage_authorized,
            "consent_id": r.consent_id,
        },
        "risk_assessment": {
            "risk_level": r.risk_level,
            "risk_score": r.risk_score,
            "components": r.risk_components or {},
            "reasons": r.risk_reasons or [],
        },
        "report_hash": r.report_hash,
        "audit_trail": events,
    }
