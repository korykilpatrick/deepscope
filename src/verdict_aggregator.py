from typing import List, Dict, Any

def aggregate_verdicts(fact_check_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine multiple source checks for each claim to produce an overall result.
    Example approach:
      - If any source strongly refutes => 'false'
      - If multiple sources support => 'true'
      - If no data => 'unverified'
      - If conflicting => 'conflicting'
    """
    if not fact_check_results:
        return {"final_verdict": "no_claims", "confidence": 0.0}

    mismatch_count = 0
    match_count = 0

    for r in fact_check_results:
        sources = r.get("checked_sources", [])
        for s in sources:
            verification = s.get("verification")
            if verification == "mismatch":
                mismatch_count += 1
            elif verification == "match":
                match_count += 1

    # Naive logic (extend as needed)
    if mismatch_count > 0 and match_count == 0:
        return {"final_verdict": "false", "confidence": 0.8}
    elif match_count > 0 and mismatch_count == 0:
        return {"final_verdict": "true", "confidence": 0.8}
    elif match_count > 0 and mismatch_count > 0:
        return {"final_verdict": "conflicting", "confidence": 0.6}
    else:
        return {"final_verdict": "unverified", "confidence": 0.5}