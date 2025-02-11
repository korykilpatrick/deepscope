from typing import List, Dict, Any
from datetime import datetime
import statistics

def aggregate_source_results(source_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    match_count = sum(1 for r in source_results if r.get("verification") == "match")
    mismatch_count = sum(1 for r in source_results if r.get("verification") == "mismatch")
    conflicting_count = sum(1 for r in source_results if r.get("verification") == "conflicting")
    total_sources = len(source_results)
    sources_with_data = sum(1 for r in source_results if r.get("verification") != "no_data")

    if match_count == 0 and mismatch_count == 0 and conflicting_count == 0:
        return {
            "verdict": {
                "status": "unverified",
                "confidence": 0.0,
                "summary": "No sources provided relevant data"
            },
            "sources": source_results,
            "metadata": {
                "processing_time": None,
                "sources_checked": total_sources,
                "sources_with_data": sources_with_data
            }
        }
    if conflicting_count > 0:
        return {
            "verdict": {
                "status": "conflicting",
                "confidence": 0.5,
                "summary": "Sources provided contradictory findings"
            },
            "sources": source_results,
            "metadata": {
                "processing_time": None,
                "sources_checked": total_sources,
                "sources_with_data": sources_with_data
            }
        }

    if match_count > mismatch_count:
        confidence = match_count / (match_count + mismatch_count)
        return {
            "verdict": {
                "status": "true",
                "confidence": confidence,
                "summary": f"Claim appears to be true based on {match_count} supporting sources"
            },
            "sources": source_results,
            "metadata": {
                "processing_time": None,
                "sources_checked": total_sources,
                "sources_with_data": sources_with_data
            }
        }
    elif mismatch_count > match_count:
        confidence = mismatch_count / (match_count + mismatch_count)
        return {
            "verdict": {
                "status": "false",
                "confidence": confidence,
                "summary": f"Claim appears to be false based on {mismatch_count} contradicting sources"
            },
            "sources": source_results,
            "metadata": {
                "processing_time": None,
                "sources_checked": total_sources,
                "sources_with_data": sources_with_data
            }
        }
    else:
        return {
            "verdict": {
                "status": "conflicting",
                "confidence": 0.5,
                "summary": "Equal match/mismatch, so final result is conflicting"
            },
            "sources": source_results,
            "metadata": {
                "processing_time": None,
                "sources_checked": total_sources,
                "sources_with_data": sources_with_data
            }
        }

def aggregate_verdicts(claims_results: List[Dict[str, Any]], processing_times: Dict[str, float] = None) -> Dict[str, Any]:
    if processing_times is None:
        processing_times = {}

    aggregated_results = []
    verified_claims = 0
    confidences = []

    for claim_result in claims_results:
        claim_text = claim_result.get("claim_text", "")
        source_results = claim_result.get("checked_sources", [])

        aggregated = aggregate_source_results(source_results)

        result = {
            "claim": {
                "text": claim_text,
                "timestamp": datetime.utcnow().isoformat(),
                "language": "en",
                "source_context": claim_result.get("source_context", "")
            },
            **aggregated
        }
        if claim_text in processing_times:
            result["metadata"]["processing_time"] = processing_times[claim_text]

        status = result["verdict"]["status"]
        if status not in ["unverified", "conflicting"]:
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