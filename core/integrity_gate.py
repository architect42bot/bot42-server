# core/integrity_gate.py
from core.response_integrity import ResponseIntegrity

def enforce_integrity(resp: ResponseIntegrity) -> ResponseIntegrity:
    # Rule 1: No unbacked "high confidence" claims
    for section in (resp.known_facts, resp.grey_areas, resp.speculation):
        for c in section:
            if c.confidence == "high" and c.evidence in ("limited_sources", "theoretical", "none"):
                c.confidence = "medium"
                c.notes += " | Confidence downgraded due to limited evidence."

    # Rule 2: Speculation must be labeled low confidence
    for c in resp.speculation:
        if c.confidence != "low":
            c.confidence = "low"
            c.notes += " | Speculation is low confidence by definition."

    return resp