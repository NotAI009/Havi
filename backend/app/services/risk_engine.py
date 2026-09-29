"""
Havi - Risk Engine.
Combines all three verification layers into a unified risk assessment.

Risk = 0.40 × spoof_probability
     + 0.30 × identity_uncertainty
     + 0.20 × consent_risk
     + 0.10 × usage_mismatch

Score | Level
------+--------
0–30  | LOW
31–60 | MEDIUM
61–100| HIGH

These weights are the prototype's risk policy, not scientifically established constants.
"""

from ..models.schemas import RiskLevel


# Risk weights
WEIGHT_SPOOF = 0.40
WEIGHT_IDENTITY = 0.30
WEIGHT_CONSENT = 0.20
WEIGHT_USAGE = 0.10

# Thresholds
THRESHOLD_LOW = 30
THRESHOLD_MEDIUM = 60


def compute_risk(
    speaker_similarity: float,
    synthetic_probability: float,
    consent_found: bool,
    consent_status: str,
    purpose_match: bool,
    usage_authorized: bool,
) -> dict:
    """
    Compute overall risk score from the three verification layers.
    
    Example LOW risk:
        Speaker Verification  92%    →  identity_uncertainty = 8%
        Voice Authenticity     24%    →  spoof_probability = 24%
        Consent Validity       100%
        Usage Match           YES
        → Risk score ~15 → LOW
    
    Example HIGH risk:
        Speaker Verification  94%    →  identity_uncertainty = 6%
        Voice Authenticity     82%    →  spoof_probability = 82%
        Consent Validity       0%
        Usage Match           NO
        → Risk score ~68 → HIGH
    """
    # Component 1: Spoof probability (0-100)
    spoof_score = synthetic_probability * 100
    
    # Component 2: Identity uncertainty (0-100)
    # Lower similarity = higher risk
    identity_score = (1.0 - speaker_similarity) * 100
    
    # Component 3: Consent risk (0-100)
    if not consent_found:
        consent_score = 100.0
    elif consent_status == "EXPIRED":
        consent_score = 80.0
    elif consent_status == "REVOKED":
        consent_score = 90.0
    elif consent_status == "ACTIVE":
        consent_score = 0.0
    else:
        consent_score = 50.0
    
    # Component 4: Usage mismatch (0-100)
    if not consent_found:
        usage_score = 100.0
    elif not purpose_match:
        usage_score = 100.0
    elif not usage_authorized:
        usage_score = 80.0
    else:
        usage_score = 0.0
    
    # Weighted risk score
    risk_score = (
        WEIGHT_SPOOF * spoof_score +
        WEIGHT_IDENTITY * identity_score +
        WEIGHT_CONSENT * consent_score +
        WEIGHT_USAGE * usage_score
    )
    
    # Clamp to [0, 100]
    risk_score = max(0.0, min(100.0, risk_score))
    
    # Determine risk level
    if risk_score <= THRESHOLD_LOW:
        risk_level = RiskLevel.LOW
    elif risk_score <= THRESHOLD_MEDIUM:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.HIGH
    
    # Generate reasons
    reasons = _generate_reasons(
        speaker_similarity, synthetic_probability,
        consent_found, consent_status,
        purpose_match, usage_authorized,
        risk_level
    )
    
    return {
        "risk_level": risk_level.value,
        "risk_score": round(risk_score, 2),
        "components": {
            "spoof_contribution": round(WEIGHT_SPOOF * spoof_score, 2),
            "identity_contribution": round(WEIGHT_IDENTITY * identity_score, 2),
            "consent_contribution": round(WEIGHT_CONSENT * consent_score, 2),
            "usage_contribution": round(WEIGHT_USAGE * usage_score, 2),
        },
        "reasons": reasons,
    }


def _generate_reasons(
    similarity: float, synthetic_prob: float,
    consent_found: bool, consent_status: str,
    purpose_match: bool, usage_authorized: bool,
    risk_level: RiskLevel
) -> list[str]:
    """Generate human-readable reasons for the risk assessment."""
    reasons = []
    
    if risk_level == RiskLevel.LOW:
        if similarity > 0.85:
            reasons.append("Voice appears consistent with registered speaker")
        if synthetic_prob < 0.3:
            reasons.append("Audio shows natural speech characteristics")
        if consent_found and consent_status == "ACTIVE":
            reasons.append("Consent record verified")
        if usage_authorized:
            reasons.append("Usage matches permitted purposes")
    
    elif risk_level == RiskLevel.MEDIUM:
        if similarity < 0.80:
            reasons.append(f"Moderate speaker similarity ({similarity:.0%})")
        if 0.3 <= synthetic_prob <= 0.6:
            reasons.append("Some synthetic speech indicators detected")
        if consent_found and consent_status != "ACTIVE":
            reasons.append(f"Consent record status: {consent_status}")
        if not purpose_match:
            reasons.append("Claimed usage does not match consent permissions")
    
    else:  # HIGH
        if similarity > 0.85 and synthetic_prob > 0.5:
            reasons.append("Potential synthetic voice impersonating registered speaker")
        elif similarity < 0.60:
            reasons.append("Speaker identity could not be verified")
        
        if synthetic_prob > 0.5:
            reasons.append("Strong synthetic speech indicators detected")
        
        if not consent_found:
            reasons.append("No valid consent record found")
        elif consent_status == "REVOKED":
            reasons.append("Consent has been revoked")
        elif consent_status == "EXPIRED":
            reasons.append("Consent record has expired")
        
        if not usage_authorized:
            reasons.append("Unverified usage authorization")
    
    if not reasons:
        reasons.append("Assessment based on combined verification signals")
    
    return reasons
