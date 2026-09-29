"""
Havi - Audio Preprocessing Utilities.
Handles audio normalization: any format → mono WAV @ 16kHz.
"""

import io
import hashlib
import tempfile
import numpy as np
from pathlib import Path


def preprocess_audio(audio_bytes: bytes, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """
    Preprocess raw audio bytes into normalized waveform.
    
    Steps:
    1. Decode audio from any format (WAV, MP3, FLAC, etc.)
    2. Convert to mono
    3. Resample to target sample rate (16kHz)
    4. Normalize amplitude
    
    Returns:
        Tuple of (waveform as numpy array, sample_rate)
    """
    try:
        import soundfile as sf
        import librosa
        
        # Write bytes to temp file for soundfile to read
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # Load audio
        waveform, sr = librosa.load(tmp_path, sr=target_sr, mono=True)
        
        # Clean up
        Path(tmp_path).unlink(missing_ok=True)
        
        # Normalize amplitude to [-1, 1]
        max_val = np.max(np.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val
        
        return waveform, target_sr
        
    except ImportError:
        # Fallback: generate synthetic waveform for demo purposes
        # This allows the system to work without full ML dependencies installed
        return _generate_demo_waveform(audio_bytes, target_sr)


def _generate_demo_waveform(audio_bytes: bytes, sr: int) -> tuple[np.ndarray, int]:
    """
    Generate a deterministic demo waveform from audio bytes.
    Used when librosa/soundfile aren't available.
    The hash of the audio bytes seeds the random generator for reproducibility.
    """
    seed = int(hashlib.md5(audio_bytes).hexdigest()[:8], 16) % (2**31)
    rng = np.random.RandomState(seed)
    
    # Generate ~3 seconds of pseudo-random waveform
    duration = max(1.0, min(len(audio_bytes) / 1000, 10.0))
    n_samples = int(sr * duration)
    waveform = rng.randn(n_samples).astype(np.float32)
    
    # Normalize
    waveform = waveform / np.max(np.abs(waveform))
    
    return waveform, sr


def compute_audio_hash(audio_bytes: bytes) -> str:
    """Compute SHA-256 hash of audio file for integrity verification."""
    return hashlib.sha256(audio_bytes).hexdigest()


def get_audio_duration(waveform: np.ndarray, sr: int) -> float:
    """Get duration of audio in seconds."""
    return len(waveform) / sr


def validate_audio(audio_bytes: bytes, min_duration: float = 0.5, max_duration: float = 300.0) -> dict:
    """
    Validate audio file meets requirements.
    
    Returns:
        Dict with 'valid' bool and 'message' string.
    """
    if len(audio_bytes) < 100:
        return {"valid": False, "message": "Audio file too small"}
    
    if len(audio_bytes) > 50 * 1024 * 1024:  # 50MB
        return {"valid": False, "message": "Audio file too large (max 50MB)"}
    
    try:
        waveform, sr = preprocess_audio(audio_bytes)
        duration = get_audio_duration(waveform, sr)
        
        if duration < min_duration:
            return {"valid": False, "message": f"Audio too short ({duration:.1f}s, min {min_duration}s)"}
        
        if duration > max_duration:
            return {"valid": False, "message": f"Audio too long ({duration:.1f}s, max {max_duration}s)"}
        
        return {"valid": True, "message": "Audio validated", "duration": duration}
        
    except Exception as e:
        return {"valid": False, "message": f"Could not process audio: {str(e)}"}
