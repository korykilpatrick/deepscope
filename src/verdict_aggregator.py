from typing import List, Dict, Any

def aggregate_verdicts(fact_check_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine multiple source checks for each claim to produce an overall result.
    For now, we do a naive approach: if any source says 'mismatch', we call 'false',
    if any says 'match', we call 'true'. Otherwise 'unverified'.
    """
    if not fact_check_results:
        return {"final_verdict": "no_claims", "confidence": 0.0}

    mismatch_count = 0
    match_count = 0

    for r in fact_check_results:
        sources = r.get("checked_sources", [])
        for s in sources:
            if s.get("verification") == "mismatch":
                mismatch_count += 1
            elif s.get("verification") == "match":
                match_count += 1

    # Very naive logic:
    if mismatch_count > 0:
        return {"final_verdict": "false", "confidence": 0.8}
    elif match_count > 0:
        return {"final_verdict": "true", "confidence": 0.8}
    else:
        return {"final_verdict": "unverified", "confidence": 0.5}