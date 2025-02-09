from fastapi import FastAPI, HTTPException
from .firebase_interface import get_transcript, update_transcript_status
from .claim_extractor import extract_claims
from .factchecker import check_fact
from .verdict_aggregator import aggregate_verdicts

app = FastAPI()

@app.get("/videos/{video_id}/raw")
async def get_raw_transcript(video_id: str):
    """Test endpoint to verify raw transcript data retrieval."""
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")
    return {
        "video_id": video_id,
        "raw_data": transcript
    }

@app.get("/videos/{video_id}/claims")
async def get_claims(video_id: str):
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")
    # Extract claims from the transcript text
    claims = extract_claims(transcript.get("text", ""))
    # For each claim, perform fact-checking
    results = []
    for claim in claims:
        verdict = check_fact(claim)
        results.append({"claim_text": claim, "verdict": verdict})
    return {"video_id": video_id, "claims": results}

@app.post("/videos/{video_id}/process")
async def process_transcript(video_id: str):
    transcript = get_transcript(video_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Video transcript not found")
    # Dummy processing: extract, verify, then update status
    claims = extract_claims(transcript.get("text", ""))
    dummy_verdicts = [check_fact(claim) for claim in claims]
    aggregated = aggregate_verdicts(dummy_verdicts)
    update_transcript_status(video_id, "processed")
    return {
        "video_id": video_id,
        "status": "processed",
        "aggregated_verdict": aggregated
    }