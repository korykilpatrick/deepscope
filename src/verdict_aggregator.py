from typing import List, Dict, Any
from datetime import datetime
import statistics

def aggregate_source_results(source_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates results from multiple fact-checking sources for a single claim.
    Returns detailed verdict with confidence and metadata.
    """
    match_count = sum(1 for r in source_results if r.get("verification") == "match")
    mismatch_count = sum(1 for r in source_results if r.get("verification") == "mismatch")
    total_sources = len(source_results)
    sources_with_data = sum(1 for r in source_results if r.get("verification") != "no_data")
    
    # Determine verdict status and confidence
    if match_count == 0 and mismatch_count == 0:
        status = "unverified"
        confidence = 0.0
        summary = "No fact-checking sources had relevant information about this claim"
    elif match_count > mismatch_count:
        status = "true"
        confidence = match_count / (match_count + mismatch_count)
        summary = f"Claim appears to be true based on {match_count} supporting sources"
    elif mismatch_count > match_count:
        status = "false"
        confidence = mismatch_count / (match_count + mismatch_count)
        summary = f"Claim appears to be false based on {mismatch_count} contradicting sources"
    else:
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
            "processing_time": None,  # To be filled by caller
            "sources_checked": total_sources,
            "sources_with_data": sources_with_data
        }
    }

def aggregate_verdicts(claims_results: List[Dict[str, Any]], processing_times: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Aggregates verification results for multiple claims from multiple fact-check sources.
    
    Args:
        claims_results: List of results for each claim from various sources
        processing_times: Optional dict mapping claim text to processing time
    
    Returns:
        Structured response with verdicts and metadata for all claims
    """
    if processing_times is None:
        processing_times = {}
    
    aggregated_results = []
    verified_claims = 0
    confidences = []
    
    for claim_result in claims_results:
        claim_text = claim_result.get("claim_text", "")
        source_results = claim_result.get("checked_sources", [])
        
        # Aggregate results for this claim
        aggregated = aggregate_source_results(source_results)
        
        # Add claim-specific metadata
        result = {
            "claim": {
                "text": claim_text,
                "timestamp": datetime.utcnow().isoformat(),
                "language": "en",  # TODO: Make this dynamic
                "source_context": claim_result.get("source_context", "")
            },
            **aggregated  # Include verdict, sources, and metadata
        }
        
        # Add processing time if available
        if claim_text in processing_times:
            result["metadata"]["processing_time"] = processing_times[claim_text]
            
        if result["verdict"]["status"] != "unverified":
            verified_claims += 1
            confidences.append(result["verdict"]["confidence"])
            
        aggregated_results.append(result)
    
    # Calculate summary statistics
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