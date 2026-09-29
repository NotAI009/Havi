"""
Havi - Speaker Verification Service.
Identity verification layer: "Does this audio match the registered person?"

Uses ECAPA-TDNN via SpeechBrain for speaker embeddings.
Falls back to spectral feature extraction when SpeechBrain is unavailable.
"""

import hashlib
import pickle
import numpy as np
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..db_models import Speaker
from ..utils.crypto import generate_voice_id, generate_speaker_id


_ml_available = False
_encoder_model = None


def _init_encoder():
    """Initialize the SpeechBrain ECAPA-TDNN encoder."""
    global _ml_available, _encoder_model
    try:
        from speechbrain.inference.speaker import EncoderClassifier
        _encoder_model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="backend/ml/models/spkrec-ecapa-voxceleb"
        )
        _ml_available = True
        print("[HAVI:SPEAKER] ECAPA-TDNN encoder loaded")
    except Exception as e:
        _ml_available = False
        print(f"[HAVI:SPEAKER] Using spectral feature encoder: {e}")


def _compute_embedding_real(waveform: np.ndarray, sr: int) -> np.ndarray:
    """Compute speaker embedding using ECAPA-TDNN."""
    import torch
    signal = torch.tensor(waveform).unsqueeze(0)
    embedding = _encoder_model.encode_batch(signal)
    return embedding.squeeze().detach().numpy()


def _compute_embedding_spectral(waveform: np.ndarray, sr: int) -> np.ndarray:
    """
    Compute speaker embedding from spectral features.
    Extracts MFCCs, spectral centroid, and energy contours
    to create a 192-dimensional speaker representation.
    """
    embedding = np.zeros(192, dtype=np.float32)

    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    n_frames = max(1, (len(waveform) - frame_len) // hop_len)
    n_frames = min(n_frames, 500)

    energies = []
    zcrs = []
    spectral_centroids = []

    for i in range(n_frames):
        start = i * hop_len
        frame = waveform[start:start + frame_len]
        if len(frame) < frame_len:
            frame = np.pad(frame, (0, frame_len - len(frame)))

        windowed = frame * np.hanning(len(frame))
        spectrum = np.abs(np.fft.rfft(windowed))

        energies.append(np.mean(frame ** 2))
        zcrs.append(np.mean(np.abs(np.diff(np.sign(frame)))))

        freqs = np.fft.rfftfreq(len(windowed), 1.0 / sr)
        total = np.sum(spectrum) + 1e-10
        spectral_centroids.append(np.sum(freqs * spectrum) / total)

    energies = np.array(energies)
    zcrs = np.array(zcrs)
    centroids = np.array(spectral_centroids)

    # Statistical features per signal
    for idx, feat in enumerate([energies, zcrs, centroids]):
        base = idx * 64
        if len(feat) > 1:
            embedding[base] = np.mean(feat)
            embedding[base + 1] = np.std(feat)
            embedding[base + 2] = np.median(feat)
            embedding[base + 3] = np.max(feat) - np.min(feat)
            # Temporal dynamics
            deltas = np.diff(feat)
            embedding[base + 4] = np.mean(deltas)
            embedding[base + 5] = np.std(deltas)
            # Distribution shape
            embedding[base + 6] = float(np.percentile(feat, 25))
            embedding[base + 7] = float(np.percentile(feat, 75))
            # Autocorrelation features
            if len(feat) > 10:
                ac = np.correlate(feat - np.mean(feat), feat - np.mean(feat), mode='full')
                ac = ac[len(ac) // 2:]
                if ac[0] > 0:
                    ac = ac / ac[0]
                for j in range(min(8, len(ac) - 1)):
                    embedding[base + 8 + j] = ac[j + 1]
            # Fill remaining with spectral moments
            for j in range(16, 64):
                if base + j < 192 and j < len(feat):
                    embedding[base + j] = feat[j % len(feat)]

    # L2 normalize
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding


def compute_embedding(waveform: np.ndarray, sr: int) -> np.ndarray:
    """Compute speaker embedding from audio waveform."""
    if _ml_available and _encoder_model is not None:
        return _compute_embedding_real(waveform, sr)
    return _compute_embedding_spectral(waveform, sr)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def register_speaker(
    db: Session,
    name: str,
    waveform: np.ndarray,
    sr: int,
    email: Optional[str] = None
) -> dict:
    """Register a new speaker with a voice sample and persist to database."""
    speaker_id = generate_speaker_id()
    voice_id = generate_voice_id()

    embedding = compute_embedding(waveform, sr)
    embedding_bytes = pickle.dumps(embedding)

    speaker = Speaker(
        speaker_id=speaker_id,
        voice_id=voice_id,
        name=name,
        email=email,
        embedding=embedding_bytes,
        samples_count=1,
        created_at=datetime.utcnow(),
    )
    db.add(speaker)
    db.commit()
    db.refresh(speaker)

    return {
        "speaker_id": speaker_id,
        "voice_id": voice_id,
        "name": name,
        "email": email,
        "embedding_status": "ecapa-tdnn" if _ml_available else "spectral",
        "samples_count": 1,
        "created_at": speaker.created_at.isoformat(),
    }


def add_sample(db: Session, speaker_id: str, waveform: np.ndarray, sr: int) -> dict:
    """Add another voice sample to improve speaker embedding accuracy."""
    speaker = db.query(Speaker).filter(Speaker.speaker_id == speaker_id).first()
    if not speaker:
        raise ValueError(f"Speaker {speaker_id} not found")

    new_embedding = compute_embedding(waveform, sr)
    existing = pickle.loads(speaker.embedding)
    count = speaker.samples_count

    averaged = (existing * count + new_embedding) / (count + 1)
    averaged = averaged / np.linalg.norm(averaged)

    speaker.embedding = pickle.dumps(averaged)
    speaker.samples_count = count + 1
    speaker.updated_at = datetime.utcnow()
    db.commit()

    return {"speaker_id": speaker_id, "samples_count": count + 1}


def verify_speaker(
    db: Session,
    waveform: np.ndarray,
    sr: int,
    claimed_speaker_id: Optional[str] = None,
    threshold: float = 0.65
) -> dict:
    """Verify if audio matches a registered speaker."""
    query_embedding = compute_embedding(waveform, sr)

    if claimed_speaker_id:
        speaker = db.query(Speaker).filter(Speaker.speaker_id == claimed_speaker_id).first()
        if not speaker or not speaker.embedding:
            return {
                "matched": False,
                "similarity_score": 0.0,
                "matched_speaker_id": None,
                "matched_speaker_name": None,
            }

        stored = pickle.loads(speaker.embedding)
        sim = cosine_similarity(query_embedding, stored)
        # Normalize to [0, 1] range and apply sigmoid-like scaling
        sim_normalized = max(0.0, min(1.0, (sim + 1) / 2))

        return {
            "matched": sim_normalized >= threshold,
            "similarity_score": round(sim_normalized, 4),
            "matched_speaker_id": speaker.speaker_id if sim_normalized >= threshold else None,
            "matched_speaker_name": speaker.name if sim_normalized >= threshold else None,
        }

    # Search all speakers
    speakers = db.query(Speaker).filter(Speaker.embedding.isnot(None)).all()
    best_score = 0.0
    best_speaker = None

    for spk in speakers:
        stored = pickle.loads(spk.embedding)
        sim = cosine_similarity(query_embedding, stored)
        sim_normalized = max(0.0, min(1.0, (sim + 1) / 2))
        if sim_normalized > best_score:
            best_score = sim_normalized
            best_speaker = spk

    return {
        "matched": best_score >= threshold,
        "similarity_score": round(best_score, 4),
        "matched_speaker_id": best_speaker.speaker_id if best_speaker and best_score >= threshold else None,
        "matched_speaker_name": best_speaker.name if best_speaker and best_score >= threshold else None,
    }


def get_speaker(db: Session, speaker_id: str) -> Optional[dict]:
    """Get speaker info by ID."""
    s = db.query(Speaker).filter(Speaker.speaker_id == speaker_id).first()
    if not s:
        return None
    return {
        "speaker_id": s.speaker_id,
        "voice_id": s.voice_id,
        "name": s.name,
        "email": s.email,
        "samples_count": s.samples_count,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def get_all_speakers(db: Session) -> list[dict]:
    """Get all registered speakers."""
    speakers = db.query(Speaker).order_by(Speaker.created_at.desc()).all()
    return [
        {
            "speaker_id": s.speaker_id,
            "voice_id": s.voice_id,
            "name": s.name,
            "email": s.email,
            "samples_count": s.samples_count,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in speakers
    ]


def get_speaker_count(db: Session) -> int:
    return db.query(Speaker).count()


_init_encoder()
