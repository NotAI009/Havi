"""
Havi - Speaker Registration Router.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import speaker, audit
from ..utils.audio import preprocess_audio, validate_audio

router = APIRouter(prefix="/api/speakers", tags=["Speakers"])


@router.post("/register")
async def register_speaker_endpoint(
    name: str = Form(...),
    audio: UploadFile = File(...),
    email: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Register a new speaker with a voice sample."""
    audio_bytes = await audio.read()
    validation = validate_audio(audio_bytes)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])

    waveform, sr = preprocess_audio(audio_bytes)
    result = speaker.register_speaker(db, name=name, waveform=waveform, sr=sr, email=email)

    audit.log_event(db, "SPEAKER_REGISTERED", {
        "speaker_id": result["speaker_id"],
        "voice_id": result["voice_id"],
        "name": name,
    })

    return result


@router.post("/{speaker_id}/samples")
async def add_voice_sample(
    speaker_id: str,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Add another voice sample to improve speaker embedding accuracy."""
    audio_bytes = await audio.read()
    validation = validate_audio(audio_bytes)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])

    waveform, sr = preprocess_audio(audio_bytes)
    try:
        result = speaker.add_sample(db, speaker_id, waveform, sr)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.get("")
async def list_speakers(db: Session = Depends(get_db)):
    """List all registered speakers."""
    speakers = speaker.get_all_speakers(db)
    return {"speakers": speakers, "total": len(speakers)}


@router.get("/{speaker_id}")
async def get_speaker_endpoint(speaker_id: str, db: Session = Depends(get_db)):
    """Get speaker info by ID."""
    spk = speaker.get_speaker(db, speaker_id)
    if not spk:
        raise HTTPException(status_code=404, detail="Speaker not found")
    return spk
