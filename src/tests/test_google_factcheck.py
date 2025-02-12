import httpx
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Load environment variables
load_dotenv()

def format_firebase_result(claim: str, response_data: dict) -> dict:
    """Format the result as it would appear in Firebase"""
    claims_data = response_data.get("claims", [])
    if not claims_data:
        return {
            "source_name": "Google Fact Check Tools Claims",
            "verification": "no_data",
            "evidence": {"api_response": "No claims returned by Google"},
            "source_url": ""
        }

    all_reviews = []
    match_count = 0
    mismatch_count = 0
    
    for item in claims_data:
        reviews = item.get("claimReview", [])
        for rev in reviews:
            rating = rev.get("textualRating", "").lower()
            # Same logic as in fact_check_service.py
            if any(indicator in rating for indicator in ["incorrect", "false", "untrue", "misleading", "wrong", "inaccurate", "debunked", "no evidence", "not true", "mostly false"]):
                mismatch_count += 1
            elif any(indicator in rating for indicator in ["correct", "true", "accurate", "verified", "confirmed", "supported by evidence", "factual", "mostly true"]):
                match_count += 1
            rev_copy = rev.copy()
            all_reviews.append(rev_copy)

    if match_count == 0 and mismatch_count == 0:
        final_verification = "no_data"
    elif match_count > 0 and mismatch_count == 0:
        final_verification = "match"
    elif mismatch_count > 0 and match_count == 0:
        final_verification = "mismatch"
    else:
        final_verification = "conflicting"

    return {
        "source_name": "Google Fact Check Tools Claims",
        "verification": final_verification,
        "evidence": {"claim_reviews": all_reviews, "raw_data": response_data},
        "source_url": ""
    }

def test_google_factcheck():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables")
        return

    # Test the Warren Buffett quote
    buffett_claim = "Warren Buffett says that when investors own portions of outstanding businesses with outstanding managements, the preferred holding period for those investments is forever."
    
    # Also test some variations to see if we get better results
    test_claims = [
        buffett_claim,  # Full quote
        "Warren Buffett says the preferred holding period is forever",  # Shortened version
        "Warren Buffett investment holding period forever",  # Key terms only
        "Warren Buffett investment advice holding period"  # Even more general
    ]

    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    
    for claim in test_claims:
        print(f"\n\nTesting claim: '{claim}'")
        print("-" * 80)
        
        params = {
            "key": api_key,
            "query": claim,
            "languageCode": "en-US"
        }

        try:
            response = httpx.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Format as it would appear in Firebase
                firebase_format = format_firebase_result(claim, data)
                print("\nAs stored in Firebase:")
                print(json.dumps(firebase_format, indent=2))
                
                # Print raw number of claims found
                claims_found = len(data.get("claims", []))
                print(f"\nNumber of claims found: {claims_found}")
                
                if claims_found == 0:
                    print("WARNING: No claims found for this query")
            else:
                print(f"\nError Response:")
                print(response.text)
                
        except Exception as e:
            print(f"Error making request: {str(e)}")

if __name__ == "__main__":
    test_google_factcheck() 