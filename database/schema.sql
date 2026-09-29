-- Havi Database Schema
-- Consent-Aware Voice Authentication & Deepfake Detection

-- Speakers table
CREATE TABLE IF NOT EXISTS speakers (
    speaker_id TEXT PRIMARY KEY,
    voice_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    embedding BLOB,  -- Encrypted speaker embedding
    samples_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Consent records
CREATE TABLE IF NOT EXISTS consent_records (
    consent_id TEXT PRIMARY KEY,
    speaker_id TEXT NOT NULL REFERENCES speakers(speaker_id),
    voice_id TEXT NOT NULL,
    person_name TEXT NOT NULL,
    purpose TEXT NOT NULL,
    permitted_usage TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'EXPIRED', 'REVOKED')),
    revoked_at TIMESTAMP,
    record_hash TEXT NOT NULL
);

-- Verification reports
CREATE TABLE IF NOT EXISTS verification_reports (
    report_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    audio_hash TEXT NOT NULL,
    speaker_similarity REAL,
    synthetic_probability REAL,
    consent_status TEXT,
    risk_level TEXT CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    risk_score REAL,
    report_data TEXT,  -- JSON blob of full report
    report_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail (tamper-evident chain)
CREATE TABLE IF NOT EXISTS audit_log (
    event_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    details TEXT,  -- JSON
    previous_hash TEXT,
    entry_hash TEXT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_consent_speaker ON consent_records(speaker_id);
CREATE INDEX IF NOT EXISTS idx_consent_status ON consent_records(status);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_reports_risk ON verification_reports(risk_level);
