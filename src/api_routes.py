from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict, Any
from datetime import datetime

from .dependencies import (
    get_firebase_db,
    get_fact_checker_service,
    get_logger_dep,
)
from .services.transcript_service import TranscriptService
from .services.claim_service import ClaimService
from .chains.base import FullFactCheckingChain
from .models.schemas import Evidence, FactCheckSource
from pydantic import BaseModel, Field

router = APIRouter()

def get_transcript_service(db=Depends(get_firebase_db)):
    return TranscriptService(db=db)

def get_full_fact_checking_chain(fact_checker=Depends(get_fact_checker_service)):
    from .chains.base import FullFactCheckingChain
    chain = FullFactCheckingChain(fact_checker=fact_checker)
    return chain

def get_claim_service(chain=Depends(get_full_fact_checking_chain)):
    return ClaimService(chain=chain)

@router.get("/videos", response_model=List[Dict[str, Any]])
async def get_videos(
    transcript_svc: TranscriptService = Depends(get_transcript_service)
):
    try:
        return transcript_svc.get_all_videos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos/{video_id}/raw")
async def get_raw_transcript(
    video_id: str,
    transcript_svc: TranscriptService = Depends(get_transcript_service)
):
    transcript = transcript_svc.get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")
    return {"video_id": video_id, "raw_data": transcript}

@router.get("/videos/{video_id}/claims")
async def get_claims(
    video_id: str,
    transcript_svc: TranscriptService = Depends(get_transcript_service),
    claim_svc: ClaimService = Depends(get_claim_service)
):
    transcript = transcript_svc.get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")

    result = await claim_svc.process_text(transcript.get("raw_text", ""))
    return {
        "video_id": video_id,
        "claims": result["claims"],
        "fact_check_results": result["fact_check_results"]
    }

async def process_claims_in_background(
    video_id: str,
    transcript_svc: TranscriptService,
    claim_svc: ClaimService
):
    transcript = transcript_svc.get_transcript(video_id)
    if not transcript:
        return

    # 1) Run the pipeline
    result = await claim_svc.process_text(transcript.get("raw_text", ""))
    fact_check_results = result["fact_check_results"]
    claims = result["claims"]

    to_store = []
    for i, claim_data in enumerate(fact_check_results):
        claim_text = claims[i].get("text", "")
        start_time = claims[i].get("start_time", "")
        end_time = claims[i].get("end_time", "")

        # Store the fact check results using the new Pydantic models
        fact_check_doc = {
            "claim_text": claim_text,
            "start_time": start_time,
            "end_time": end_time,
            "sources": [source.model_dump() for source in claim_data.get("sources", [])]
        }
        to_store.append(fact_check_doc)

    transcript_svc.store_fact_check_results(video_id, to_store)
    transcript_svc.update_transcript_status(video_id, "processed")

@router.post("/videos/{video_id}/process")
async def process_transcript(
    video_id: str,
    background_tasks: BackgroundTasks,
    transcript_svc: TranscriptService = Depends(get_transcript_service),
    claim_svc: ClaimService = Depends(get_claim_service)
):
    if not transcript_svc.get_transcript(video_id):
        raise HTTPException(status_code=404, detail="Transcript not found")

    transcript_svc.update_transcript_status(video_id, "in_progress")
    background_tasks.add_task(process_claims_in_background, video_id, transcript_svc, claim_svc)
    return {
        "video_id": video_id,
        "status": "started_processing"
    }

class TextInput(BaseModel):
    text: str

@router.post("/extract-claims")
async def extract_claims_from_text(
    input_data: TextInput,
    chain=Depends(get_full_fact_checking_chain)
):
    try:
        result = chain.claim_extractor({"transcript": input_data.text})
        return {"claims": result["output"] or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ClaimRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_context: str = ""

class BatchClaimRequest(BaseModel):
    claims: List[ClaimRequest] = Field(..., min_items=1)

class FactCheckResponse(BaseModel):
    claim_text: str
    sources: List[FactCheckSource]

class BatchFactCheckResponse(BaseModel):
    results: List[FactCheckResponse]

@router.post("/check-claim", response_model=FactCheckResponse)
async def verify_claim(
    request: ClaimRequest,
    fact_checker=Depends(get_fact_checker_service)
):
    try:
        results = await fact_checker.check_facts([request.text])
        return results[0] if results else {
            "claim_text": request.text,
            "sources": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")

@router.post("/check-claims", response_model=BatchFactCheckResponse)
async def verify_claims(
    request: BatchClaimRequest,
    fact_checker=Depends(get_fact_checker_service)
):
    try:
        claims = [c.text for c in request.claims]
        results = await fact_checker.check_facts(claims)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claims: {str(e)}")

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "deepscope-factcheck"}

@router.post("/videos/{video_id}/reset")
async def reset_video(
    video_id: str,
    transcript_svc: TranscriptService = Depends(get_transcript_service)
):
    """Reset a video by completely removing fact check results collection and setting status to pending"""
    try:
        # Get the video document
        doc_ref = transcript_svc.db.collection('videos').document(video_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Recursively delete the entire fact_check_results collection
        fact_checks_ref = doc_ref.collection('fact_check_results')
        transcript_svc.db.recursiveDelete(fact_checks_ref)
            
        # Reset status and clean up the empty array field
        doc_ref.update({
            'status': 'pending',
            'fact_check_results': transcript_svc.db.field_path('fact_check_results').delete()
        })
        
        return {"status": "success", "message": f"Reset video {video_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))