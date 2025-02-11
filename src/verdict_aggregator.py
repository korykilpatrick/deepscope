from typing import List, Dict, Any

def aggregate_verdicts(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates the verification results from multiple fact-check sources.
    Expects each result to have a 'verification' key with one of:
      - "match" (supports the claim)
      - "mismatch" (refutes the claim)
      - "no_data" (no useful info)
    
    Aggregation logic:
      - If both match and mismatch are zero, return "unverified".
      - If matches outnumber mismatches, verdict is "true" with confidence
        proportional to the ratio.
      - If mismatches outnumber matches, verdict is "false" similarly.
      - If counts are equal and nonzero, verdict is "conflicting" with medium confidence.
    """
    match_count = sum(1 for r in results if r.get("verification") == "match")
    mismatch_count = sum(1 for r in results if r.get("verification") == "mismatch")
    
    if match_count == 0 and mismatch_count == 0:
        return {"final_verdict": "unverified", "confidence": 0.0}
    if match_count > mismatch_count:
        confidence = match_count / (match_count + mismatch_count)
        return {"final_verdict": "true", "confidence": confidence}
    elif mismatch_count > match_count:
        confidence = mismatch_count / (match_count + mismatch_count)
        return {"final_verdict": "false", "confidence": confidence}
    else:
        return {"final_verdict": "conflicting", "confidence": 0.5}