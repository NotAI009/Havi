# Havi

> **Consent-Aware Voice Authentication & Deepfake Detection**

Havi is a cybersecurity-first voice identity framework. Rather than just detecting deepfakes or identifying speakers, Havi solves the core enterprise problem of **consent verification**. It ensures that a voice belongs to the claimed identity, is authentic (non-synthetic), and critically, is authorized for the specific usage intent.

## Architecture

Havi operates across three distinct verification layers integrated with a proprietary Risk Engine:

1. **Speaker Identity Layer**: Determines if the audio matches the registered biometric profile of the user. Uses ECAPA-TDNN embeddings (via SpeechBrain/PyTorch) or robust spectral feature analysis as a fallback.
2. **Authenticity Layer (Spoof Detection)**: Analyzes the audio for synthetic anomalies, utilizing spectral energy, zero-crossing rate variance, and jitter to detect deepfakes or voice cloning attempts.
3. **Consent Verification Layer**: Validates against a cryptographically hashed registry. It checks if the speaker has explicitly authorized the *specific purpose* of the current usage.
4. **Risk Engine**: A weighted scoring mechanism that evaluates the outputs of the three layers and computes an actionable risk level (`LOW`, `MEDIUM`, `HIGH`).
5. **Tamper-Evident Audit Trail**: Every API event (verification, registration, consent lifecycle) is logged via SHA-256 hash chaining, guaranteeing the integrity of historical records.

## Tech Stack

- **Backend**: FastAPI (Python), SQLAlchemy, SpeechBrain, Librosa, PyTorch
- **Frontend**: React + Vite, Custom CSS (MNC-level Glassmorphism Design, zero Tailwind)
- **Database**: SQLite (Development) / PostgreSQL (Production ready)

## Quick Start

### 1. Backend (API & ML Pipeline)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (Dashboard)
```bash
cd frontend
npm install
npm run dev
```

### Demo Mode
Upon startup, the database is automatically seeded with 5 demo speakers, multiple consent records, and a generated verification history so the dashboard works instantly out of the box.

## API Documentation
Once the backend is running, the interactive Swagger documentation is available at:
`http://localhost:8000/docs`

---
*Developed for a cybersecurity hackathon.*
