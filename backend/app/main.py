"""
Havi — Consent-Aware Voice Authentication & Deepfake Detection.
Main FastAPI application.
"""

import numpy as np
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import get_db, init_db, SessionLocal
from .routers import verify, register, consent, audit
from .services import speaker as speaker_svc
from .services import consent as consent_svc
from .services import audit as audit_svc
from .db_models import Speaker, VerificationReport


def seed_data():
    """Seed initial data for the system."""
    db = SessionLocal()
    try:
        if db.query(Speaker).count() > 0:
            return  # Already seeded

        print("\n  Seeding initial data...")

        demo_speakers = [
            {"name": "Rahul Sharma", "email": "rahul.sharma@havi.io"},
            {"name": "Ananya Rao", "email": "ananya.rao@havi.io"},
            {"name": "Vikram Patel", "email": "vikram.patel@havi.io"},
            {"name": "Priya Nair", "email": "priya.nair@havi.io"},
            {"name": "Arjun Reddy", "email": "arjun.reddy@havi.io"},
        ]

        speaker_ids = []
        for spk in demo_speakers:
            seed_val = hash(spk["name"]) % (2**31)
            rng = np.random.RandomState(abs(seed_val))
            waveform = rng.randn(16000 * 3).astype(np.float32)
            waveform = waveform / np.max(np.abs(waveform))

            result = speaker_svc.register_speaker(
                db, name=spk["name"], waveform=waveform, sr=16000, email=spk["email"]
            )
            speaker_ids.append(result["speaker_id"])
            print(f"    + Speaker: {spk['name']} → {result['speaker_id']}")

        consent_data = [
            (0, "AI Assistant", ["Personal assistant", "Smart home"], 365),
            (1, "Advertisement", ["TV commercial"], -30),  # Pre-expired
            (2, "Authentication", ["Banking", "Office access"], 365),
            (3, "Education", ["Online courses", "Lecture recordings"], 180),
            (4, "Research", ["Academic study", "Voice analysis"], 365),
        ]

        for idx, purpose, usage, days in consent_data:
            spk = speaker_svc.get_speaker(db, speaker_ids[idx])
            consent_svc.create_consent(
                db,
                speaker_id=speaker_ids[idx],
                voice_id=spk["voice_id"],
                person_name=spk["name"],
                purpose=purpose,
                permitted_usage=usage,
                expires_days=days,
            )

        # Seed some verification history
        for i in range(8):
            rng = np.random.RandomState(42 + i)
            waveform = rng.randn(16000 * 2).astype(np.float32)
            waveform = waveform / np.max(np.abs(waveform))

            from .services import deepfake, risk_engine
            spk_result = speaker_svc.verify_speaker(db, waveform, 16000)
            df_result = deepfake.detect_deepfake(waveform, 16000)

            target_id = spk_result.get("matched_speaker_id") or speaker_ids[i % len(speaker_ids)]
            c_result = consent_svc.verify_consent(db, target_id)

            risk = risk_engine.compute_risk(
                speaker_similarity=spk_result["similarity_score"],
                synthetic_probability=df_result["synthetic_probability"],
                consent_found=c_result["consent_found"],
                consent_status=c_result["consent_status"],
                purpose_match=c_result["purpose_match"],
                usage_authorized=c_result["usage_authorized"],
            )

            from ..app.utils.crypto import generate_report_id, hash_consent_record
            report_id = generate_report_id()
            report_hash = hash_consent_record({"id": report_id, "i": i})

            report = VerificationReport(
                report_id=report_id,
                filename=f"sample_{i+1}.wav",
                audio_hash=f"hash_{i}",
                file_size=16000 * 2 * 2,
                duration=2.0,
                speaker_similarity=spk_result["similarity_score"],
                speaker_matched=spk_result["matched"],
                matched_speaker_id=spk_result.get("matched_speaker_id"),
                matched_speaker_name=spk_result.get("matched_speaker_name"),
                synthetic_probability=df_result["synthetic_probability"],
                is_synthetic=df_result["is_synthetic"],
                deepfake_confidence=df_result["confidence"],
                deepfake_indicators=df_result["indicators"],
                consent_found=c_result["consent_found"],
                consent_status=c_result["consent_status"],
                purpose_match=c_result["purpose_match"],
                usage_authorized=c_result["usage_authorized"],
                risk_level=risk["risk_level"],
                risk_score=risk["risk_score"],
                risk_components=risk["components"],
                risk_reasons=risk["reasons"],
                report_hash=report_hash,
                created_at=datetime.utcnow() - timedelta(hours=8-i),
            )
            db.add(report)

            audit_svc.log_event(db, "SPEAKER_VERIFIED", {
                "similarity": spk_result["similarity_score"],
                "matched_speaker": spk_result.get("matched_speaker_name"),
            }, report_id=report_id)
            audit_svc.log_event(db, "RISK_ENGINE", {
                "risk_level": risk["risk_level"],
                "risk_score": risk["risk_score"],
                "filename": f"sample_{i+1}.wav",
            }, report_id=report_id)
            if risk["risk_level"] == "HIGH":
                audit_svc.log_event(db, "ALERT_GENERATED", {
                    "risk_level": "HIGH",
                    "filename": f"sample_{i+1}.wav",
                }, report_id=report_id)

        db.commit()
        print(f"    Seeded: {len(speaker_ids)} speakers, {len(consent_data)} consents, 8 reports\n")

    except Exception as e:
        print(f"    Seed error (non-critical): {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    print("\n" + "=" * 56)
    print("  HAVI — Consent-Aware Voice Authentication")
    print("  & Deepfake Detection System  v1.0.0")
    print("=" * 56)
    init_db()
    print("  Database initialized")
    seed_data()
    print("  API:      http://localhost:8000/docs")
    print("  Frontend: http://localhost:5173")
    print("=" * 56 + "\n")
    yield


app = FastAPI(
    title="Havi",
    description="Consent-Aware Voice Authentication & Deepfake Detection",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(verify.router)
app.include_router(register.router)
app.include_router(consent.router)
app.include_router(audit.router)


@app.get("/")
async def root():
    return {
        "name": "Havi",
        "tagline": "Consent-Aware Voice Authentication & Deepfake Detection",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/api/dashboard")
async def dashboard(db: Session = Depends(get_db)):
    """Dashboard statistics and recent activity."""
    from sqlalchemy import func, desc

    total_reports = db.query(VerificationReport).count()
    high_risk = db.query(VerificationReport).filter(VerificationReport.risk_level == "HIGH").count()
    avg_risk = db.query(func.avg(VerificationReport.risk_score)).scalar() or 0

    recent = db.query(VerificationReport).order_by(
        desc(VerificationReport.created_at)
    ).limit(10).all()

    return {
        "protected_voices": speaker_svc.get_speaker_count(db),
        "verified_recordings": total_reports,
        "suspicious_attempts": high_risk,
        "active_consents": consent_svc.get_active_consents_count(db),
        "avg_risk_score": round(avg_risk, 1),
        "recent_verifications": [
            {
                "report_id": r.report_id,
                "filename": r.filename,
                "risk_level": r.risk_level,
                "risk_score": r.risk_score,
                "speaker_similarity": r.speaker_similarity,
                "synthetic_probability": r.synthetic_probability,
                "matched_speaker_name": r.matched_speaker_name,
                "consent_status": r.consent_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent
        ],
    }
