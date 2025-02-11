from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import asyncio
from pydantic import BaseModel, Field

from src.firebase_interface import (
    get_transcript,
    update_transcript_status,
    get_all_videos,
    store_fact_check_results
)
from src.chains.base import FullFactCheckingChain

router = APIRouter()

# Initialize the chain
fact_checking_chain = FullFactCheckingChain()

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
    Extract claims and verify them using the fact checking pipeline.
    Not recommended for large transcripts in production.
    """
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")

    result = await fact_checking_chain.acall({"text": transcript.get("text", "")})
    return {
        "video_id": video_id,
        "claims": result["claims"],
        "verdicts": result["verdicts"],
        "final_result": result["final_result"]
    }

async def process_claims_in_background(video_id: str):
    """
    Async pipeline using LangChain for processing claims.
    """
    transcript = get_transcript(video_id)
    if not transcript:
        return

    result = await fact_checking_chain.acall({"text": transcript.get("text", "")})
    
    to_store = []
    for claim, verdict in zip(result["claims"], result["verdicts"]):
        to_store.append({
            "claim_text": claim,
            "checked_sources": verdict.get("checked_sources", []),
            "final_verdict": verdict.get("verdict", {}).get("status", "unknown")
        })

    store_fact_check_results(video_id, to_store)
    update_transcript_status(
        video_id, 
        f"processed_with_verdict_{result['final_result'].get('status', 'unknown')}"
    )

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

class TextInput(BaseModel):
    text: str

@router.post("/extract-claims", response_model=Dict[str, List[str]])
async def extract_claims_from_text(input_data: TextInput):
    """
    Extract claims from raw text input.
    
    Args:
        input_data: TextInput object containing the text to analyze
        
    Returns:
        Dictionary containing list of extracted claims
    """
    try:
        result = fact_checking_chain.claim_extractor({"input_text": input_data.text})
        return {"claims": result["output"] if result["output"] else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ClaimRequest(BaseModel):
    text: str = Field(..., description="The claim text to verify", min_length=1)
    source_context: str = Field("", description="Optional context about where the claim came from")

class BatchClaimRequest(BaseModel):
    claims: List[ClaimRequest] = Field(..., description="List of claims to verify", min_items=1)

@router.post("/check-claim",
    response_model=Dict[str, Any],
    summary="Check a single claim",
    description="Verifies a single claim using multiple fact-checking sources"
)
async def verify_claim(request: ClaimRequest):
    try:
        result = await fact_checking_chain.fact_verifier._acall({"input_text": request.text})
        verdict = result["output"]
        
        if request.source_context and "claim" in verdict:
            verdict["claim"]["source_context"] = request.source_context
            
        return verdict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")

@router.post("/check-claims",
    response_model=Dict[str, Any],
    summary="Check multiple claims",
    description="Verifies multiple claims using multiple fact-checking sources"
)
async def verify_claims(request: BatchClaimRequest):
    try:
        claims = [claim.text for claim in request.claims]
        result = await fact_checking_chain.fact_verifier._acall({"input_text": claims})
        verdict = result["output"]
        
        # Add source context to each result if provided
        for i, claim_request in enumerate(request.claims):
            if claim_request.source_context and i < len(verdict["aggregated_results"]):
                verdict["aggregated_results"][i]["claim"]["source_context"] = claim_request.source_context
                
        return verdict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claims: {str(e)}")

# Health check endpoint
@router.get("/health",
    summary="Health check",
    description="Check if the API is running"
)
async def health_check():
    return {"status": "healthy", "service": "deepscope-factcheck"}