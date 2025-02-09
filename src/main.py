from fastapi import FastAPI, HTTPException
from .firebase_interface import get_transcript, update_transcript_status
from .claim_extractor import extract_claims
from .factchecker import check_fact
from .verdict_aggregator import aggregate_verdicts

app = FastAPI()

@app.get("/transcripts/{transcript_id}/claims")
async def get_claims(transcript_id: str):
    transcript = get_transcript(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    # Extract claims from the transcript text
    claims = extract_claims(transcript.get("text", ""))
    # For each claim, perform fact-checking
    results = []
    for claim in claims:
        verdict = check_fact(claim)
        results.append({"claim_text": claim, "verdict": verdict})
    return {"transcript_id": transcript_id, "claims": results}

@app.post("/transcripts/{transcript_id}/process")
async def process_transcript(transcript_id: str):
    transcript = get_transcript(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    # Dummy processing: extract, verify, then update status
    claims = extract_claims(transcript.get("text", ""))
    dummy_verdicts = [check_fact(claim) for claim in claims]
    aggregated = aggregate_verdicts(dummy_verdicts)
    update_transcript_status(transcript_id, "processed")
    return {
        "transcript_id": transcript_id,
        "status": "processed",
        "aggregated_verdict": aggregated
    }