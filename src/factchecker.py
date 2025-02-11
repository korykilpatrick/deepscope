import asyncio
from typing import Dict, Any, List
import httpx
from dotenv import load_dotenv
import os
import time
from random import uniform

from src.verdict_aggregator import aggregate_verdicts

load_dotenv()

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

def retry_with_backoff(func, max_retries=3):
    """Retry a function with exponential backoff"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                # Add a small random delay to prevent concurrent requests
                time.sleep(uniform(0.5, 1.5))
                result = func(*args, **kwargs)
                if result.status_code != 403:  # If not rate limited, return
                    return result
                # If rate limited, wait before retry
                time.sleep((2 ** attempt) + uniform(0, 1))
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep((2 ** attempt) + uniform(0, 1))
        return result
    return wrapper

# New function using the Google Fact Check Tools API (Claims endpoint)
def check_with_google_factcheck(claim: str) -> Dict:
    """
    Uses the Google Fact Check Tools API Claims endpoint to attempt to verify a claim.
    Returns a structured response containing the verification result and supporting evidence.
    """
    url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        "key": os.getenv('GOOGLE_API_KEY'),
        "query": claim,
        "languageCode": "en-US"
    }
    try:
        # Wrap the request in retry logic
        get_with_retry = retry_with_backoff(lambda: httpx.get(url, params=params))
        response = get_with_retry()
        
        print(f"\nMaking request to: {url}")
        print(f"With params: {params}")
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            claims = data.get("claims", [])
            if claims:
                # Get the first relevant claim
                claim_data = claims[0]
                return {
                    "source_name": "Google Fact Check Tools Claims",
                    "verification": "match",
                    "evidence": {
                        "claim_review": claim_data.get("claimReview", []),
                        "text": claim_data.get("text", ""),
                        "claimant": claim_data.get("claimant", "")
                    },
                    "source_url": claim_data.get("claimReview", [{}])[0].get("url", "")
                }
        return {
            "source_name": "Google Fact Check Tools Claims",
            "verification": "no_data",
            "evidence": {"api_response": response.text if response.status_code == 200 else f"Status code: {response.status_code}"},
            "source_url": ""
        }
    except Exception as e:
        print(f"Error in Google Fact Check API call: {str(e)}")
        return {
            "source_name": "Google Fact Check Tools Claims",
            "verification": "no_data",
            "evidence": {"error": str(e)},
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