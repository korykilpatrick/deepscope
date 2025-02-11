import asyncio
from typing import Dict, Any, List, Protocol
import httpx
from dotenv import load_dotenv
import os
import time
from random import uniform
from datetime import datetime

from src.verdict_aggregator import aggregate_verdicts

load_dotenv()

class FactCheckSource(Protocol):
    """Protocol defining interface for fact checking sources"""
    def check_claim(self, claim: str) -> Dict[str, Any]:
        """Check a claim and return structured results"""
        pass

class GoogleFactCheckAPI:
    """Google Fact Check Tools API implementation"""
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment")

    @staticmethod
    def retry_with_backoff(func, max_retries=3):
        """Retry a function with exponential backoff"""
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    time.sleep(uniform(0.5, 1.5))
                    result = func(*args, **kwargs)
                    if result.status_code != 403:
                        return result
                    time.sleep((2 ** attempt) + uniform(0, 1))
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep((2 ** attempt) + uniform(0, 1))
            return result
        return wrapper

    def _interpret_rating(self, textual_rating: str) -> str:
        """
        Interpret the textual rating from Google Fact Check API.
        Returns: "match", "mismatch", or "no_data"
        """
        if not textual_rating:
            return "no_data"
            
        # Convert to lowercase for easier matching
        rating_lower = textual_rating.lower()
        
        # Keywords indicating false claims
        false_indicators = [
            "incorrect", "false", "untrue", "misleading", "wrong",
            "inaccurate", "debunked", "no evidence", "not true"
        ]
        
        # Keywords indicating true claims
        true_indicators = [
            "correct", "true", "accurate", "verified", "confirmed",
            "supported by evidence", "factual"
        ]
        
        # Check for false indicators first as they're more definitive
        for indicator in false_indicators:
            if indicator in rating_lower:
                return "mismatch"
                
        # Then check for true indicators
        for indicator in true_indicators:
            if indicator in rating_lower:
                return "match"
                
        # If no clear indication, return no_data
        return "no_data"

    def check_claim(self, claim: str) -> Dict[str, Any]:
        """Check a claim using Google Fact Check Tools API"""
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "key": self.api_key,
            "query": claim,
            "languageCode": "en-US"
        }
        try:
            get_with_retry = self.retry_with_backoff(lambda: httpx.get(url, params=params))
            response = get_with_retry()
            
            if response.status_code == 200:
                data = response.json()
                claims = data.get("claims", [])
                if claims:
                    claim_data = claims[0]
                    claim_reviews = claim_data.get("claimReview", [])
                    
                    if claim_reviews:
                        # Get the most recent review
                        review = claim_reviews[0]
                        verification = self._interpret_rating(review.get("textualRating", ""))
                        
                        return {
                            "source_name": "Google Fact Check Tools Claims",
                            "verification": verification,
                            "evidence": {
                                "claim_review": claim_reviews,
                                "text": claim_data.get("text", ""),
                                "claimant": claim_data.get("claimant", "")
                            },
                            "source_url": review.get("url", "")
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

class FactChecker:
    """Main fact checker that coordinates multiple fact checking sources"""
    def __init__(self):
        self.sources: List[FactCheckSource] = [
            GoogleFactCheckAPI(),
            # Add more sources here as they become available
            # Example: FactiverseAPI(), ParafactAPI(), etc.
        ]

    async def _check_with_source(self, source: FactCheckSource, claim: str) -> Dict[str, Any]:
        """Run a single source check asynchronously"""
        start_time = time.time()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, source.check_claim, claim)
        result["response_metadata"] = {
            "response_time": time.time() - start_time,
            "api_version": "v1",  # This should be source-specific
            "timestamp": datetime.utcnow().isoformat()
        }
        return result

    async def check_facts(self, claims: List[str]) -> Dict[str, Any]:
        """Check multiple facts using all available sources"""
        processing_times = {}
        claims_results = []
        
        for claim in claims:
            start_time = time.time()
            tasks = [self._check_with_source(source, claim) for source in self.sources]
            source_results = await asyncio.gather(*tasks)
            
            processing_time = time.time() - start_time
            processing_times[claim] = processing_time
            
            claims_results.append({
                "claim_text": claim,
                "checked_sources": source_results,
                "source_context": ""  # This should be populated by the caller if available
            })
        
        return aggregate_verdicts(claims_results, processing_times)

    async def check_fact(self, claim: str) -> Dict[str, Any]:
        """Check a single fact using all available sources"""
        result = await self.check_facts([claim])
        return result["aggregated_results"][0] if result["aggregated_results"] else {}

# Create a global instance for use in the API
fact_checker = FactChecker()

# Expose the main async functions for external use
async def check_fact(claim: str) -> Dict[str, Any]:
    """Public interface for fact checking a single claim"""
    return await fact_checker.check_fact(claim)

async def check_facts(claims: List[str]) -> Dict[str, Any]:
    """Public interface for fact checking multiple claims"""
    return await fact_checker.check_facts(claims)