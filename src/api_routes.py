from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict, Any

from .dependencies import (
    get_firebase_db,
    get_fact_checker_service,
    get_logger_dep,
)
from .services.transcript_service import TranscriptService
from .services.claim_service import ClaimService
from .chains.base import FullFactCheckingChain
from pydantic import BaseModel, Field

router = APIRouter()

# Create singletons via dependencies
def get_transcript_service(db=Depends(get_firebase_db)):
    return TranscriptService(db=db)

# Build the chain with injected fact checker
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
        "verdicts": result["verdicts"],
        "final_result": result["final_result"]
    }

async def process_claims_in_background(video_id: str,
                                       transcript_svc: TranscriptService,
                                       claim_svc: ClaimService):
    transcript = transcript_svc.get_transcript(video_id)
    if not transcript:
        return

    segments = transcript.get("segments", [])
    result = await claim_svc.process_text(transcript.get("raw_text", ""))

    to_store = []
    for claim, verdict in zip(result["claims"], result["verdicts"]):
        # Claims now come with timestamps
        claim_text = claim["text"] if isinstance(claim, dict) else str(claim)
        claim_start = claim.get("start_time", "") if isinstance(claim, dict) else ""
        claim_end = claim.get("end_time", "") if isinstance(claim, dict) else ""

        # Only try to find segment if we don't have timestamps
        if not claim_start or not claim_end:
            for seg in segments:
                if claim_text in seg["text"]:
                    claim_start = seg["start"]
                    claim_end = seg["end"]
                    break

        to_store.append({
            "claim_text": claim_text,
            "checked_sources": verdict.get("checked_sources", []),
            "final_verdict": verdict.get("verdict", {}).get("status", "unknown"),
            "claim_start": claim_start,
            "claim_end": claim_end
        })

    transcript_svc.store_fact_check_results(video_id, to_store)
    final_status = result["final_result"].get("status", "unknown")
    transcript_svc.update_transcript_status(video_id, f"processed_with_verdict_{final_status}")

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

@router.post("/check-claim")
async def verify_claim(
    request: ClaimRequest,
    fact_checker=Depends(get_fact_checker_service)
):
    try:
        result = await fact_checker.check_facts([request.text])
        # result is aggregated, so pull first from "aggregated_results"
        aggregated = result["aggregated_results"][0] if result.get("aggregated_results") else {}
        if request.source_context and "claim" in aggregated:
            aggregated["claim"]["source_context"] = request.source_context
        return aggregated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")

@router.post("/check-claims")
async def verify_claims(
    request: BatchClaimRequest,
    fact_checker=Depends(get_fact_checker_service)
):
    try:
        claims = [c.text for c in request.claims]
        result = await fact_checker.check_facts(claims)
        # Insert source_context
        for i, c_req in enumerate(request.claims):
            if (i < len(result["aggregated_results"]) and c_req.source_context):
                result["aggregated_results"][i]["claim"]["source_context"] = c_req.source_context
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claims: {str(e)}")

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "deepscope-factcheck"}