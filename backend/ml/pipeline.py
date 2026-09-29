"""
Havi - Standalone ML Pipeline.
Run the full verification pipeline from command line.

Usage:
    python -m ml.pipeline --audio path/to/audio.wav --speaker-id SPK-XXXXXXXX
    python -m ml.pipeline --audio path/to/audio.wav  (no claimed speaker)
"""

import argparse
import json
import sys
import os
import numpy as np

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.audio import preprocess_audio, compute_audio_hash
from app.services.speaker import verify_speaker, compute_embedding
from app.services.deepfake import detect_deepfake
from app.services.risk_engine import compute_risk


def run_pipeline(audio_path: str, claimed_speaker_id: str = None) -> dict:
    """
    Run the full ML verification pipeline on an audio file.
    
    TEST AUDIO
        ↓
    Preprocessing
        ↓
    ┌──────────┴──────────┐
    ↓                     ↓
    Speaker Verification  Deepfake Detection
    ↓                     ↓
    similarity %          spoof probability
    └──────────┬──────────┘
               ↓
           Risk Engine
               ↓
           JSON RESULT
    """
    # Read audio file
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    print(f"\n{'='*50}")
    print(f"  HAVI ML Pipeline")
    print(f"{'='*50}")
    print(f"  File: {os.path.basename(audio_path)}")
    print(f"  Size: {len(audio_bytes):,} bytes")
    print(f"  Hash: {compute_audio_hash(audio_bytes)[:16]}...")
    
    # Preprocess
    print(f"\n  [1/4] Preprocessing audio...")
    waveform, sr = preprocess_audio(audio_bytes)
    duration = len(waveform) / sr
    print(f"        Duration: {duration:.2f}s | Sample rate: {sr}Hz | Samples: {len(waveform):,}")
    
    # Speaker Verification
    print(f"\n  [2/4] Speaker verification...")
    speaker_result = verify_speaker(waveform, sr, claimed_speaker_id=claimed_speaker_id)
    print(f"        Similarity: {speaker_result['similarity_score']:.1%}")
    print(f"        Matched: {speaker_result['matched']}")
    if speaker_result.get('matched_speaker_name'):
        print(f"        Speaker: {speaker_result['matched_speaker_name']}")
    
    # Deepfake Detection
    print(f"\n  [3/4] Deepfake detection...")
    deepfake_result = detect_deepfake(waveform, sr)
    print(f"        Synthetic probability: {deepfake_result['synthetic_probability']:.1%}")
    print(f"        Is synthetic: {deepfake_result['is_synthetic']}")
    for indicator in deepfake_result['indicators']:
        print(f"        → {indicator}")
    
    # Risk Engine
    print(f"\n  [4/4] Risk assessment...")
    risk_result = compute_risk(
        speaker_similarity=speaker_result["similarity_score"],
        synthetic_probability=deepfake_result["synthetic_probability"],
        consent_found=False,  # No consent DB in standalone mode
        consent_status="NOT_FOUND",
        purpose_match=False,
        usage_authorized=False,
    )
    
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
    print(f"        Risk Level: {risk_emoji.get(risk_result['risk_level'], '⚪')} {risk_result['risk_level']}")
    print(f"        Risk Score: {risk_result['risk_score']:.1f}/100")
    for reason in risk_result['reasons']:
        print(f"        → {reason}")
    
    # Final result
    result = {
        "speaker_match": speaker_result["similarity_score"],
        "synthetic_probability": deepfake_result["synthetic_probability"],
        "consent_status": "missing",
        "usage_authorized": False,
        "risk_level": risk_result["risk_level"],
        "risk_score": risk_result["risk_score"],
    }
    
    print(f"\n{'='*50}")
    print(f"  Result JSON:")
    print(f"{'='*50}")
    print(json.dumps(result, indent=2))
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Havi ML Pipeline")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--speaker-id", default=None, help="Claimed speaker ID")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.audio):
        print(f"Error: Audio file not found: {args.audio}")
        sys.exit(1)
    
    run_pipeline(args.audio, args.speaker_id)
