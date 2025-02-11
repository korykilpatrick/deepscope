import asyncio
from typing import Dict, Any, List
import httpx

from src.verdict_aggregator import aggregate_verdicts

# can maybe later add in other apis like factiverse, parafact, etc
# Placeholder helper functions
def http_get(url: str) -> httpx.Response:
    return httpx.get(url)

def http_post(url: str, payload: dict) -> httpx.Response:
    return httpx.post(url, json=payload)

def parse_json(response: httpx.Response) -> dict:
    return response.json()

def llm_inference(prompt: str) -> str:
    # Dummy LLM inference returning a basic explanation
    return "Dummy explanation: standard verification indicates true."

def parse_llm_verdict(result: str) -> str:
    # Dummy parsing: if 'true' is in result, return "match", if 'false', "mismatch"
    if "true" in result.lower():
        return "match"
    elif "false" in result.lower():
        return "mismatch"
    return "no_data"

async def async_call(func, claim: str) -> Dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, claim)

# New function using the Google Fact Check Tools API (Pages endpoint)
def check_with_google_factcheck(claim: str) -> Dict:
    """
    Uses the Google Fact Check Tools API Pages endpoint to attempt to verify a claim.
    Fetches all available fact-check pages and returns a "match" if any page's
    claimReview contains a title or textualRating that includes the claim text.
    """
    url = f"https://factchecktools.googleapis.com/v1alpha1/pages?key=YOUR_GOOGLE_API_KEY"
    response = http_get(url)
    if response.status_code == 200:
        data = parse_json(response)
        pages = data.get("pages", [])
        for page in pages:
            claim_reviews = page.get("claimReview", [])
            for review in claim_reviews:
                title = review.get("title", "").lower()
                textual_rating = review.get("textualRating", "").lower()
                if claim.lower() in title or claim.lower() in textual_rating:
                    return {
                        "source_name": "Google Fact Check Tools Pages",
                        "verification": "match",
                        "evidence": review,
                        "source_url": page.get("pageUrl", "")
                    }
        return {
            "source_name": "Google Fact Check Tools Pages",
            "verification": "no_data",
            "evidence": {},
            "source_url": ""
        }
    return {
        "source_name": "Google Fact Check Tools Pages",
        "verification": "no_data",
        "evidence": {},
        "source_url": ""
    }

# Function for LLM-based reasoning as fallback or supplement
def check_with_llm(claim: str) -> Dict:
    prompt = f"Verify the claim: '{claim}'. Provide a brief explanation and a true/false/inconclusive verdict."
    result = llm_inference(prompt)
    return {
        "source_name": "LLM Reasoning",
        "verification": parse_llm_verdict(result),
        "evidence": {"explanation": result},
        "source_url": ""
    }

# Main fact-check function calling only the Google API and LLM fallback concurrently.
async def check_fact(claim: str) -> Dict:
    tasks = [
        async_call(check_with_google_factcheck, claim),
        async_call(check_with_llm, claim)
    ]
    results = await asyncio.gather(*tasks)
    final_verdict = aggregate_verdicts(results)
    return {
        "claim_text": claim,
        "final_verdict": final_verdict["final_verdict"],
        "confidence": final_verdict["confidence"],
        "checked_sources": results
    }