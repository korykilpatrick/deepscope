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
                    # If status 403, wait longer
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
        Returns one of: "match", "mismatch", "no_data", or "conflicting" (though typically
        "conflicting" is set at a higher level if multiple reviews disagree).
        """
        if not textual_rating:
            return "no_data"

        rating_lower = textual_rating.lower()

        # Keywords more strongly indicating "false"
        false_indicators = [
            "incorrect", "false", "untrue", "misleading", "wrong",
            "inaccurate", "debunked", "no evidence", "not true", "mostly false"
        ]
        # Keywords more strongly indicating "true"
        true_indicators = [
            "correct", "true", "accurate", "verified", "confirmed",
            "supported by evidence", "factual", "mostly true"
        ]

        # Check for false indicators first
        for indicator in false_indicators:
            if indicator in rating_lower:
                return "mismatch"

        # Then check for true indicators
        for indicator in true_indicators:
            if indicator in rating_lower:
                return "match"

        # If no clear match
        return "no_data"

    def check_claim(self, claim: str) -> Dict[str, Any]:
        """
        Query Google Fact Check Tools API for all relevant claim entries and
        produce a single verification by combining them (match/mismatch/conflicting/no_data).
        Also include all reviews in evidence.
        """
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "key": self.api_key,
            "query": claim,
            "languageCode": "en-US"
        }

        # Prepare default fallback structure
        def no_data_result(api_response_text=""):
            return {
                "source_name": "Google Fact Check Tools Claims",
                "verification": "no_data",
                "evidence": {"api_response": api_response_text},
                "source_url": ""
            }

        try:
            get_with_retry = self.retry_with_backoff(lambda: httpx.get(url, params=params))
            response = get_with_retry()
            if response.status_code != 200:
                return no_data_result(f"Status code: {response.status_code}")

            data = response.json()
            claims = data.get("claims", [])
            if not claims:
                # No claims found
                return no_data_result("No claims returned by Google")

            # Collect all reviews
            all_reviews = []
            match_count = 0
            mismatch_count = 0

            for item in claims:
                reviews = item.get("claimReview", [])
                for rev in reviews:
                    textual_rating = rev.get("textualRating", "")
                    interpreted = self._interpret_rating(textual_rating)

                    all_reviews.append({
                        "url": rev.get("url", ""),
                        "publisher_name": rev.get("publisher", {}).get("name", ""),
                        "title": rev.get("title", ""),
                        "textual_rating": textual_rating,
                        "interpreted_rating": interpreted
                    })

                    if interpreted == "match":
                        match_count += 1
                    elif interpreted == "mismatch":
                        mismatch_count += 1

            # Decide final single verification label for Google
            if not all_reviews:
                # Means claims list was non-empty but no claimReview found
                return no_data_result("No claimReview data found")

            # If we have reviews, check the tallies
            if match_count == 0 and mismatch_count == 0:
                final_verification = "no_data"
            elif match_count > 0 and mismatch_count == 0:
                final_verification = "match"
            elif mismatch_count > 0 and match_count == 0:
                final_verification = "mismatch"
            else:
                # Some are match, some are mismatch => "conflicting"
                final_verification = "conflicting"

            return {
                "source_name": "Google Fact Check Tools Claims",
                "verification": final_verification,
                "evidence": {
                    "claim_reviews": all_reviews
                },
                "source_url": ""
            }

        except Exception as e:
            # Fail-safe
            return {
                "source_name": "Google Fact Check Tools Claims",
                "verification": "no_data",
                "evidence": {"error": str(e)},
                "source_url": ""
            }

class FactChecker:
    """Main fact checker that coordinates multiple fact checking sources"""
    def __init__(self):
        # Add additional sources as needed
        self.sources: List[FactCheckSource] = [
            GoogleFactCheckAPI(),
        ]

    async def _check_with_source(self, source: FactCheckSource, claim: str) -> Dict[str, Any]:
        """Run a single source check asynchronously"""
        start_time = time.time()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, source.check_claim, claim)
        result["response_metadata"] = {
            "response_time": time.time() - start_time,
            "api_version": "v1",  # This could be source-specific if you want
            "timestamp": datetime.utcnow().isoformat()
        }
        return result

    async def check_facts(self, claims: List[str]) -> Dict[str, Any]:
        """
        Check multiple claims using all available sources.
        Returns aggregated verdicts across each claim.
        """
        processing_times = {}
        claims_results = []

        for claim in claims:
            start_time = time.time()
            tasks = [self._check_with_source(source, claim) for source in self.sources]
            source_results = await asyncio.gather(*tasks)
            processing_time = time.time() - start_time
            processing_times[claim] = processing_time

            # Store raw results so aggregator can interpret them
            claims_results.append({
                "claim_text": claim,
                "checked_sources": source_results,
                "source_context": ""
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