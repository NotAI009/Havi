"""
Havi - Cryptographic Utilities.
Tamper-evident audit chains, consent record signing, and embedding encryption.
"""

import hashlib
import json
import hmac
import secrets
from datetime import datetime


# Server-side secret for HMAC operations
# In production, this comes from environment variables
_SERVER_SECRET = secrets.token_hex(32)


def hash_event(event_data: dict, previous_hash: str = "") -> str:
    """
    Create a SHA-256 hash of an event, chained to the previous hash.
    This creates a tamper-evident audit chain.
    
    event_001 → SHA-256 → a91c...82f
    event_002 → previous_hash + event → SHA-256 → c41a...19d
    
    If any event in the chain is modified, all subsequent hashes become invalid.
    """
    # Canonicalize the event data
    canonical = json.dumps(event_data, sort_keys=True, default=str)
    
    # Chain: previous_hash + canonical_event
    chain_input = f"{previous_hash}:{canonical}"
    
    return hashlib.sha256(chain_input.encode('utf-8')).hexdigest()


def verify_chain(events: list[dict]) -> bool:
    """
    Verify the integrity of an audit chain.
    Each event must contain 'entry_hash' and 'previous_hash' fields.
    
    Returns True if the chain is intact, False if tampering is detected.
    """
    for i, event in enumerate(events):
        expected_previous = events[i - 1]["entry_hash"] if i > 0 else ""
        
        if event.get("previous_hash", "") != expected_previous:
            return False
        
        # Recompute hash without the entry_hash field
        event_data = {k: v for k, v in event.items() if k != "entry_hash"}
        computed = hash_event(event_data, expected_previous)
        
        if computed != event["entry_hash"]:
            return False
    
    return True


def hash_consent_record(consent_data: dict) -> str:
    """
    Generate a cryptographic hash for a consent record.
    Used to detect unauthorized modifications to consent records.
    """
    canonical = json.dumps(consent_data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def generate_consent_id() -> str:
    """Generate a unique consent ID in format HV-YYYY-XXXXX."""
    year = datetime.now().year
    unique = secrets.token_hex(3).upper()
    return f"HV-{year}-{unique}"


def generate_voice_id() -> str:
    """Generate a unique voice ID in format V-XXXXXX."""
    return f"V-{secrets.token_hex(3).upper()}"


def generate_speaker_id() -> str:
    """Generate a unique speaker ID."""
    return f"SPK-{secrets.token_hex(4).upper()}"


def generate_report_id() -> str:
    """Generate a unique verification report ID."""
    return f"RPT-{secrets.token_hex(4).upper()}"


def generate_event_id() -> str:
    """Generate a unique audit event ID."""
    return f"EVT-{secrets.token_hex(4).upper()}"


def sign_data(data: str) -> str:
    """
    Create an HMAC signature for data using the server secret.
    Used for verifying data integrity in consent records.
    """
    return hmac.new(
        _SERVER_SECRET.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_signature(data: str, signature: str) -> bool:
    """Verify an HMAC signature."""
    expected = sign_data(data)
    return hmac.compare_digest(expected, signature)
