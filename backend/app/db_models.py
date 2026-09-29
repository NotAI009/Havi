"""
Havi - SQLAlchemy ORM Models.
Persistent storage for speakers, consent records, verification reports, and audit trails.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, LargeBinary, JSON
from sqlalchemy.orm import relationship
from .database import Base


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    speaker_id = Column(String(32), unique=True, nullable=False, index=True)
    voice_id = Column(String(32), unique=True, nullable=False)
    name = Column(String(256), nullable=False)
    email = Column(String(256))
    embedding = Column(LargeBinary)  # Serialized numpy array
    samples_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consents = relationship("ConsentRecord", back_populates="speaker", cascade="all, delete-orphan")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    consent_id = Column(String(32), unique=True, nullable=False, index=True)
    speaker_id = Column(String(32), ForeignKey("speakers.speaker_id"), nullable=False)
    voice_id = Column(String(32), nullable=False)
    person_name = Column(String(256), nullable=False)
    purpose = Column(String(128), nullable=False)
    permitted_usage = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(32), default="ACTIVE", index=True)
    revoked_at = Column(DateTime)
    record_hash = Column(String(128), nullable=False)

    speaker = relationship("Speaker", back_populates="consents")


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(32), unique=True, nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    audio_hash = Column(String(128))
    file_size = Column(Integer)
    duration = Column(Float)

    # Speaker verification results
    speaker_similarity = Column(Float)
    speaker_matched = Column(Boolean, default=False)
    matched_speaker_id = Column(String(32))
    matched_speaker_name = Column(String(256))

    # Deepfake detection results
    synthetic_probability = Column(Float)
    is_synthetic = Column(Boolean, default=False)
    deepfake_confidence = Column(Float)
    deepfake_indicators = Column(JSON, default=list)

    # Consent verification results
    consent_found = Column(Boolean, default=False)
    consent_status = Column(String(32))
    purpose_match = Column(Boolean, default=False)
    usage_authorized = Column(Boolean, default=False)
    consent_id = Column(String(32))

    # Risk assessment
    risk_level = Column(String(16), index=True)
    risk_score = Column(Float)
    risk_components = Column(JSON, default=dict)
    risk_reasons = Column(JSON, default=list)

    report_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(32), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    details = Column(JSON, default=dict)
    report_id = Column(String(32), index=True)
    previous_hash = Column(String(128), default="")
    entry_hash = Column(String(128), nullable=False)


class AnalyticsSnapshot(Base):
    """Aggregated analytics data for dashboard performance."""
    __tablename__ = "analytics_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    total_speakers = Column(Integer, default=0)
    total_verifications = Column(Integer, default=0)
    total_alerts = Column(Integer, default=0)
    active_consents = Column(Integer, default=0)
    avg_risk_score = Column(Float, default=0.0)
    synthetic_detections = Column(Integer, default=0)
    genuine_detections = Column(Integer, default=0)
