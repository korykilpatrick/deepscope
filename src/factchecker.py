import asyncio
from typing import Dict, Any, List, Protocol
import httpx
from dotenv import load_dotenv
import os
import time
from random import uniform
from datetime import datetime
import json

# Import the new OpenAI client class
from openai import OpenAI

from src.verdict_aggregator import aggregate_verdicts

load_dotenv()

class FactCheckSource(Protocol):
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
        Returns one of: "match", "mismatch", "no_data", or "conflicting".
        """
        if not textual_rating:
            return "no_data"

        rating_lower = textual_rating.lower()

        false_indicators = [
            "incorrect", "false", "untrue", "misleading", "wrong",
            "inaccurate", "debunked", "no evidence", "not true", "mostly false"
        ]
        true_indicators = [
            "correct", "true", "accurate", "verified", "confirmed",
            "supported by evidence", "factual", "mostly true"
        ]

        for indicator in false_indicators:
            if indicator in rating_lower:
                return "mismatch"

        for indicator in true_indicators:
            if indicator in rating_lower:
                return "match"

        return "no_data"

    def check_claim(self, claim: str) -> Dict[str, Any]:
        """
        Query Google Fact Check Tools API for all relevant claim entries and
        produce a single verification by combining them. Also include all reviews in evidence.
        """
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "key": self.api_key,
            "query": claim,
            "languageCode": "en-US"
        }

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
                return no_data_result("No claims returned by Google")

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

            if not all_reviews:
                return no_data_result("No claimReview data found")

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
                "evidence": {
                    "claim_reviews": all_reviews
                },
                "source_url": ""
            }

        except Exception as e:
            return {
                "source_name": "Google Fact Check Tools Claims",
                "verification": "no_data",
                "evidence": {"error": str(e)},
                "source_url": ""
            }

class LLMFactCheckAPI:
    """LLM-based fact checker using GPT-4 with the new OpenAI API interface"""
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        # Instantiate the new OpenAI client
        self.client = OpenAI(api_key=self.api_key)

    def check_claim(self, claim: str) -> Dict[str, Any]:
        prompt = (
            "You are a fact-checking assistant. Evaluate the following claim for its truthfulness. "
            "Return your response as a JSON object with the following keys: "
            "'verdict' (one of 'true', 'false', 'uncertain'), "
            "'confidence' (a number between 0 and 1), "
            "'explanation' (a brief explanation), and "
            "'reference_links' (an array of URLs that provide supporting evidence, if available). "
            "If you are confident the claim is true or false, set 'verdict' accordingly. "
            "Otherwise, set it to 'uncertain'. Do not include any additional text. "
            f"Claim: {claim}"
        )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a reliable fact-checker."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            message_content = response.choices[0].message.content
            result_json = json.loads(message_content)
            verdict = result_json.get("verdict", "uncertain").lower()
            mapping = {"true": "match", "false": "mismatch", "uncertain": "no_data"}
            verification = mapping.get(verdict, "no_data")
            confidence = result_json.get("confidence", 0)
            explanation = result_json.get("explanation", "")
            reference_links = result_json.get("reference_links", [])
            return {
                "source_name": "LLM Fact Checker",
                "verification": verification,
                "evidence": {
                    "explanation": explanation,
                    "reference_links": reference_links,
                    "confidence": confidence
                },
                "source_url": ""
            }
        except Exception as e:
            return {
                "source_name": "LLM Fact Checker",
                "verification": "no_data",
                "evidence": {"error": str(e), "confidence": 0},
                "source_url": ""
            }

class FactChecker:
    """
    Hybrid fact checker that first uses an LLM-based check.
    If the LLM is sufficiently confident (confidence >= threshold),
    its result is returned along with any reference links. Otherwise,
    the system falls back to using Google Fact Check Tools.
    """
    def __init__(self):
        self.llm_source = LLMFactCheckAPI()
        self.google_source = GoogleFactCheckAPI()
        self.llm_confidence_threshold = 0.8

    async def _check_llm(self, claim: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.llm_source.check_claim, claim)

    async def _check_google(self, claim: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.google_source.check_claim, claim)

    async def check_fact(self, claim: str) -> Dict[str, Any]:
        llm_result = await self._check_llm(claim)
        confidence = llm_result.get("evidence", {}).get("confidence", 0)
        if confidence >= self.llm_confidence_threshold:
            return llm_result
        else:
            google_result = await self._check_google(claim)
            return google_result

    async def check_facts(self, claims: List[str]) -> Dict[str, Any]:
        processing_times = {}
        claims_results = []
        for claim in claims:
            start_time = time.time()
            result = await self.check_fact(claim)
            processing_time = time.time() - start_time
            processing_times[claim] = processing_time
            claims_results.append({
                "claim_text": claim,
                "checked_sources": [result],
                "source_context": ""
            })
        return aggregate_verdicts(claims_results, processing_times)

# Create a global instance for external use
fact_checker = FactChecker()

async def check_fact(claim: str) -> Dict[str, Any]:
    """Public interface for fact checking a single claim"""
    return await fact_checker.check_fact(claim)

async def check_facts(claims: List[str]) -> Dict[str, Any]:
    """Public interface for fact checking multiple claims"""
    return await fact_checker.check_facts(claims)