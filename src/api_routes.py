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
        return videos
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
    Extract claims and do basic verification (blocking call).
    Not recommended for large transcripts in production.
    """
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")

    extracted_claims = extract_claims(transcript.get("text", ""))
    if not extracted_claims:
        return {"video_id": video_id, "claims": []}

    checked_claims = []
    for claim in extracted_claims:
        loop = asyncio.get_event_loop()
        fact_result = loop.run_until_complete(check_fact(claim))
        checked_claims.append(fact_result)

    return {"video_id": video_id, "claims": checked_claims}

async def process_claims_in_background(video_id: str):
    """
    Async pipeline:
      - extract claims
      - run checks in parallel
      - aggregate results
      - store in Firebase
      - update transcript status
    """
    transcript = get_transcript(video_id)
    if not transcript:
        return

    extracted_claims = extract_claims(transcript.get("text", ""))
    tasks = [check_fact(c) for c in extracted_claims]
    results = await asyncio.gather(*tasks)

    final_verdict = aggregate_verdicts(results)

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
    Launches background processing for large transcripts.
    """
    if not get_transcript(video_id):
        raise HTTPException(status_code=404, detail="Transcript not found")

    update_transcript_status(video_id, "in_progress")
    background_tasks.add_task(process_claims_in_background, video_id)
    return {
        "video_id": video_id,
        "status": "started_processing"
    }