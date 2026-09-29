"""
Havi - Deepfake / Synthetic Voice Detection Service.
Answers: "Does this audio appear to be genuine human speech or 
         synthetically generated/manipulated speech?"

This is separate from speaker verification. A cloned voice can pass
speaker verification (high similarity) while still being synthetic.
That's the cybersecurity problem this layer addresses.

Uses spectral analysis and ML-based anti-spoofing features.
Falls back to heuristic-based detection for demo mode.
"""

import hashlib
import numpy as np
from typing import Optional


# Track ML availability
_ml_available = False
_spoof_model = None


def _init_spoof_detector():
    """Try to initialize a pretrained anti-spoofing model."""
    global _ml_available, _spoof_model
    
    try:
        # Try to load a spoof detection model
        # In production, this would be an ASVspoof-trained model
        import torch
        
        # Check if a custom model exists
        import os
        model_path = "backend/ml/models/spoof_detector.pt"
        if os.path.exists(model_path):
            _spoof_model = torch.load(model_path, map_location="cpu")
            _ml_available = True
            print("[DEEPFAKE] ✓ Anti-spoof model loaded")
        else:
            print("[DEEPFAKE] ⚠ No spoof model found, using heuristic mode")
            _ml_available = False
            
    except Exception as e:
        _ml_available = False
        print(f"[DEEPFAKE] ⚠ ML not available, using heuristic mode: {e}")


def _extract_spectral_features(waveform: np.ndarray, sr: int) -> dict:
    """
    Extract spectral features that help distinguish real vs synthetic speech.
    
    Key indicators of synthetic speech:
    - Unnaturally smooth spectral envelopes
    - Missing or artificial micro-variations
    - Unusual spectral rolloff patterns
    - Lack of natural breathing/noise artifacts
    """
    features = {}
    
    # Segment the audio
    frame_len = int(0.025 * sr)  # 25ms frames
    hop_len = int(0.010 * sr)    # 10ms hop
    
    n_frames = max(1, (len(waveform) - frame_len) // hop_len)
    
    # Frame-level energy
    energies = []
    zero_crossings = []
    
    for i in range(min(n_frames, 500)):  # Cap at 500 frames
        start = i * hop_len
        frame = waveform[start:start + frame_len]
        
        if len(frame) == 0:
            continue
            
        energies.append(np.mean(frame**2))
        zero_crossings.append(np.mean(np.abs(np.diff(np.sign(frame)))))
    
    if not energies:
        return {"spectral_smoothness": 0.5, "energy_variance": 0.5, "zcr_variance": 0.5}
    
    energies = np.array(energies)
    zero_crossings = np.array(zero_crossings)
    
    # Feature 1: Energy variance (synthetic speech tends to have more uniform energy)
    features["energy_variance"] = float(np.var(energies)) if len(energies) > 1 else 0.0
    
    # Feature 2: Zero-crossing rate variance
    features["zcr_variance"] = float(np.var(zero_crossings)) if len(zero_crossings) > 1 else 0.0
    
    # Feature 3: Spectral smoothness (synthetic tends to be smoother)
    # Approximate via autocorrelation of energy contour
    if len(energies) > 10:
        autocorr = np.correlate(energies - np.mean(energies), energies - np.mean(energies), mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        if autocorr[0] > 0:
            autocorr = autocorr / autocorr[0]
        features["spectral_smoothness"] = float(np.mean(autocorr[1:min(10, len(autocorr))]))
    else:
        features["spectral_smoothness"] = 0.5
    
    # Feature 4: Silence ratio (real speech has natural pauses)
    silence_threshold = np.percentile(energies, 10) * 2
    features["silence_ratio"] = float(np.mean(energies < silence_threshold))
    
    # Feature 5: Jitter approximation (pitch perturbation, absent in synthetic)
    if len(energies) > 2:
        jitter = np.mean(np.abs(np.diff(energies))) / (np.mean(energies) + 1e-10)
        features["jitter"] = float(jitter)
    else:
        features["jitter"] = 0.0
    
    return features


def _heuristic_spoof_score(features: dict) -> tuple[float, list[str]]:
    """
    Compute a heuristic spoofing probability from spectral features.
    
    This is a simplified scoring system for demo purposes.
    In production, this would be replaced by a trained neural network.
    
    Higher score = more likely synthetic.
    """
    score = 0.0
    indicators = []
    
    # Low energy variance → possibly synthetic
    if features.get("energy_variance", 0) < 0.001:
        score += 0.25
        indicators.append("Unnaturally uniform energy distribution")
    elif features.get("energy_variance", 0) < 0.005:
        score += 0.10
    
    # Low ZCR variance → possibly synthetic
    if features.get("zcr_variance", 0) < 0.001:
        score += 0.20
        indicators.append("Suspiciously smooth spectral envelope")
    elif features.get("zcr_variance", 0) < 0.005:
        score += 0.08
    
    # High spectral smoothness → possibly synthetic
    smoothness = features.get("spectral_smoothness", 0.5)
    if smoothness > 0.7:
        score += 0.20
        indicators.append("Spectral smoothness exceeds natural speech patterns")
    elif smoothness > 0.5:
        score += 0.08
    
    # Very low silence ratio → possibly synthetic (no natural pauses)
    silence = features.get("silence_ratio", 0.1)
    if silence < 0.02:
        score += 0.15
        indicators.append("Absence of natural speech pauses")
    elif silence > 0.5:
        score += 0.10
        indicators.append("Unusual pause distribution")
    
    # Low jitter → possibly synthetic (too perfect)
    jitter = features.get("jitter", 0.1)
    if jitter < 0.01:
        score += 0.20
        indicators.append("Missing micro-pitch variations (too perfect)")
    elif jitter < 0.05:
        score += 0.08
    
    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))
    
    if not indicators:
        indicators.append("No significant synthetic indicators detected")
    
    return score, indicators


def detect_deepfake(waveform: np.ndarray, sr: int) -> dict:
    """
    Analyze audio for synthetic speech indicators.
    
    Returns:
        Dict with:
        - is_synthetic: bool (True if probability > 0.5)
        - synthetic_probability: float [0, 1]
        - confidence: float [0, 1]
        - indicators: list of human-readable findings
    """
    if _ml_available and _spoof_model is not None:
        return _detect_with_model(waveform, sr)
    
    return _detect_heuristic(waveform, sr)


def _detect_with_model(waveform: np.ndarray, sr: int) -> dict:
    """Use the trained ML model for detection."""
    import torch
    
    signal = torch.tensor(waveform).unsqueeze(0).unsqueeze(0)
    
    with torch.no_grad():
        output = _spoof_model(signal)
        prob = torch.sigmoid(output).item()
    
    indicators = []
    if prob > 0.7:
        indicators.append("ML model: high confidence synthetic speech")
    elif prob > 0.5:
        indicators.append("ML model: moderate synthetic speech indicators")
    else:
        indicators.append("ML model: appears to be genuine speech")
    
    return {
        "is_synthetic": prob > 0.5,
        "synthetic_probability": round(prob, 4),
        "confidence": round(abs(prob - 0.5) * 2, 4),  # Distance from decision boundary
        "indicators": indicators,
    }


def _detect_heuristic(waveform: np.ndarray, sr: int) -> dict:
    """Use heuristic spectral analysis for detection."""
    features = _extract_spectral_features(waveform, sr)
    probability, indicators = _heuristic_spoof_score(features)
    
    return {
        "is_synthetic": probability > 0.5,
        "synthetic_probability": round(probability, 4),
        "confidence": round(abs(probability - 0.5) * 2, 4),
        "indicators": indicators,
    }


# Initialize at import
_init_spoof_detector()
