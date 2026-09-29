"""
Havi - Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConsentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    NOT_FOUND = "NOT_FOUND"


class UsagePurpose(str, Enum):
    AI_ASSISTANT = "AI Assistant"
    ADVERTISEMENT = "Advertisement"
    AUTHENTICATION = "Authentication"
    ENTERTAINMENT = "Entertainment"
    EDUCATION = "Education"
    RESEARCH = "Research"
    OTHER = "Other"


class AuditEventType(str, Enum):
    VOICE_UPLOADED = "VOICE_UPLOADED"
    SPEAKER_REGISTERED = "SPEAKER_REGISTERED"
    SPEAKER_VERIFIED = "SPEAKER_VERIFIED"
    SPOOF_ANALYSIS = "SPOOF_ANALYSIS"
    CONSENT_CREATED = "CONSENT_CREATED"
    CONSENT_CHECK = "CONSENT_CHECK"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    RISK_ENGINE = "RISK_ENGINE"
    ALERT_GENERATED = "ALERT_GENERATED"


# ─── Speaker Registration ───────────────────────────────────────────

class SpeakerRegistrationRequest(BaseModel):
    name: str = Field(..., description="Full name of the speaker")
    email: Optional[str] = Field(None, description="Email address")


class SpeakerRegistrationResponse(BaseModel):
    speaker_id: str
    voice_id: str
    name: str
    embedding_status: str
    samples_count: int
    created_at: datetime


# ─── Consent ─────────────────────────────────────────────────────────

class ConsentCreateRequest(BaseModel):
    speaker_id: str
    purpose: UsagePurpose
    permitted_usage: List[str] = Field(default_factory=list)
    expires_days: int = Field(default=365, description="Days until consent expires")


class ConsentRecord(BaseModel):
    consent_id: str
    speaker_id: str
    voice_id: str
    person_name: str
    purpose: UsagePurpose
    permitted_usage: List[str]
    created_at: datetime
    expires_at: datetime
    status: ConsentStatus
    record_hash: str


class ConsentListResponse(BaseModel):
    consents: List[ConsentRecord]
    total: int


# ─── Verification ───────────────────────────────────────────────────

class VerificationRequest(BaseModel):
    claimed_speaker_id: Optional[str] = None
    claimed_purpose: Optional[str] = None


class SpeakerVerificationResult(BaseModel):
    matched: bool
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    matched_speaker_id: Optional[str] = None
    matched_speaker_name: Optional[str] = None


class DeepfakeDetectionResult(BaseModel):
    is_synthetic: bool
    synthetic_probability: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    indicators: List[str] = Field(default_factory=list)


class ConsentVerificationResult(BaseModel):
    consent_found: bool
    consent_status: ConsentStatus
    purpose_match: bool
    usage_authorized: bool
    consent_id: Optional[str] = None
    details: Optional[str] = None


class RiskAssessment(BaseModel):
    risk_level: RiskLevel
    risk_score: float = Field(..., ge=0.0, le=100.0)
    components: dict
    reasons: List[str]


class VerificationReport(BaseModel):
    report_id: str
    timestamp: datetime
    filename: str
    speaker_verification: SpeakerVerificationResult
    deepfake_detection: DeepfakeDetectionResult
    consent_verification: ConsentVerificationResult
    risk_assessment: RiskAssessment
    report_hash: str


# ─── Audit ───────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    details: dict
    previous_hash: Optional[str] = None
    entry_hash: str


class AuditTrailResponse(BaseModel):
    entries: List[AuditEntry]
    chain_valid: bool
    total: int


# ─── Dashboard ───────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    protected_voices: int
    verified_recordings: int
    suspicious_attempts: int
    active_consents: int
    recent_verifications: List[dict]
