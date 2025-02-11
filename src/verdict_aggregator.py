from typing import List, Dict, Any
from datetime import datetime
import statistics

def aggregate_source_results(source_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates results from multiple fact-checking sources for a single claim.
    Returns a structured verdict with confidence and metadata.
    """
    # Tally each source’s verification
    match_count = sum(1 for r in source_results if r.get("verification") == "match")
    mismatch_count = sum(1 for r in source_results if r.get("verification") == "mismatch")
    conflicting_count = sum(1 for r in source_results if r.get("verification") == "conflicting")
    total_sources = len(source_results)
    sources_with_data = sum(1 for r in source_results if r.get("verification") != "no_data")

    # Decide final status
    if match_count == 0 and mismatch_count == 0 and conflicting_count == 0:
        status = "unverified"
        confidence = 0.0
        summary = "No fact-checking sources had relevant information about this claim"
    elif conflicting_count > 0:
        status = "conflicting"
        confidence = 0.5  # or you can refine based on match/mismatch tallies
        summary = "At least one source indicated a match and another indicated a mismatch"
    else:
        if match_count > mismatch_count:
            status = "true"
            confidence = match_count / (match_count + mismatch_count)
            summary = f"Claim appears to be true based on {match_count} supporting sources"
        elif mismatch_count > match_count:
            status = "false"
            confidence = mismatch_count / (match_count + mismatch_count)
            summary = f"Claim appears to be false based on {mismatch_count} contradicting sources"
        else:
            # If match_count == mismatch_count (and > 0), treat as conflicting
            status = "conflicting"
            confidence = 0.5
            summary = "Sources disagree on the veracity of this claim"

    return {
        "verdict": {
            "status": status,
            "confidence": confidence,
            "summary": summary
        },
        "sources": source_results,
        "metadata": {
            "processing_time": None,  # to be filled by caller
            "sources_checked": total_sources,
            "sources_with_data": sources_with_data
        }
    }

def aggregate_verdicts(claims_results: List[Dict[str, Any]], processing_times: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Aggregates verification results for multiple claims from multiple fact-check sources.

    Args:
        claims_results: List of results for each claim from various sources.
        processing_times: Optional dict mapping claim text to processing time.

    Returns:
        A structured response with verdicts and metadata for all claims.
    """
    if processing_times is None:
        processing_times = {}

    aggregated_results = []
    verified_claims = 0
    confidences = []

    for claim_result in claims_results:
        claim_text = claim_result.get("claim_text", "")
        source_results = claim_result.get("checked_sources", [])

        # Aggregate results for this single claim
        aggregated = aggregate_source_results(source_results)

        # Attach claim-level metadata
        result = {
            "claim": {
                "text": claim_text,
                "timestamp": datetime.utcnow().isoformat(),
                "language": "en",  # could be dynamic
                "source_context": claim_result.get("source_context", "")
            },
            **aggregated  # includes 'verdict', 'sources', 'metadata'
        }

        # Fill processing time if available
        if claim_text in processing_times:
            result["metadata"]["processing_time"] = processing_times[claim_text]

        # Track aggregated confidence for claims not labeled unverified
        if result["verdict"]["status"] not in ["unverified", "conflicting"]:
            verified_claims += 1
            confidences.append(result["verdict"]["confidence"])

        aggregated_results.append(result)

    total_claims = len(aggregated_results)
    avg_confidence = statistics.mean(confidences) if confidences else 0.0

    return {
        "aggregated_results": aggregated_results,
        "summary": {
            "total_claims": total_claims,
            "verified_claims": verified_claims,
            "unverified_claims": total_claims - verified_claims,
            "average_confidence": avg_confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
    }