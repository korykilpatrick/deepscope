from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import asyncio

from src.firebase_interface import (
    get_transcript,
    update_transcript_status,
    get_all_videos,
    store_fact_check_results
)
from src.claim_extractor import extract_claims
from src.factchecker import check_fact
from src.verdict_aggregator import aggregate_verdicts

router = APIRouter()

@router.get("/videos", response_model=List[Dict[str, Any]])
async def get_videos():
    """
    Retrieve all video documents from Firebase.
    """
    try:
        videos = get_all_videos()
        return videos if videos else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos/{video_id}/raw")
async def get_raw_transcript(video_id: str):
    """
    Return unprocessed transcript data for debugging.
    """
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")
    return {"video_id": video_id, "raw_data": transcript}

@router.get("/videos/{video_id}/claims")
async def get_claims(video_id: str):
    """
    Synchronously extract claims and do partial verification (not recommended for real use).
    """
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")

    extracted_claims = extract_claims(transcript.get("text", ""))
    # We'll do a quick sequential check here (not using aggregator).
    if not extracted_claims:
        return {"video_id": video_id, "claims": []}

    # For demonstration, run checks in series (small transcripts).
    checked_claims = []
    for claim in extracted_claims:
        # Each check_fact call is async, so we gather them in a new event loop here:
        loop = asyncio.get_event_loop()
        fact_result = loop.run_until_complete(check_fact(claim))
        checked_claims.append(fact_result)

    return {"video_id": video_id, "claims": checked_claims}

async def process_claims_in_background(video_id: str):
    """
    Async flow that:
      - extracts claims
      - runs checks in parallel
      - aggregates results
      - stores them in Firebase
      - updates transcript status
    """
    transcript = get_transcript(video_id)
    if not transcript:
        return

    # Extract
    extracted_claims = extract_claims(transcript.get("text", ""))

    # Run checks concurrently for each claim
    tasks = [check_fact(c) for c in extracted_claims]
    results = await asyncio.gather(*tasks)

    # Combine verdicts across all claims
    final_verdict = aggregate_verdicts(results)

    # Prepare data to store
    # We'll store each claim's details, then store final verdict too.
    to_store = []
    for r in results:
        to_store.append({
            "claim_text": r.get("claim_text"),
            "category": r.get("category"),
            "checked_sources": r.get("checked_sources"),
        })

    store_fact_check_results(video_id, to_store)
    update_transcript_status(video_id, "processed_with_verdict_" + final_verdict["final_verdict"])

@router.post("/videos/{video_id}/process")
async def process_transcript(video_id: str, background_tasks: BackgroundTasks):
    """
    Kicks off background processing so we don't block the caller.
    Immediately returns a status message.
    """
    if not get_transcript(video_id):
        raise HTTPException(status_code=404, detail="Transcript not found")

    # Mark status, then queue an async background job
    update_transcript_status(video_id, "in_progress")
    background_tasks.add_task(process_claims_in_background, video_id)

    return {
        "video_id": video_id,
        "status": "started_processing"
    }