import asyncio
import time
import json
import httpx
from random import uniform
from typing import List, Dict, Any, Protocol
from datetime import datetime

from openai import OpenAI  # Use the new OpenAI client interface

from ..verdict_aggregator import aggregate_verdicts

# Protocol to define a common interface (optional)
class FactCheckSource(Protocol):
    def check_claim(self, claim: str) -> Dict[str, Any]:
        pass

class GoogleFactCheckAPI:
    """Google Fact Check Tools API implementation."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("Google API key not provided")
    
    @staticmethod
    def retry_with_backoff(func, max_retries=3):
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
            claims_data = data.get("claims", [])
            if not claims_data:
                return no_data_result("No claims returned by Google")
            all_reviews = []
            match_count = 0
            mismatch_count = 0
            for item in claims_data:
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
                "evidence": {"claim_reviews": all_reviews},
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
    """LLM-based fact checker using GPT-4 with the new OpenAI API interface."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not provided")
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

class FactCheckerService:
    """
    Hybrid fact checker that first uses an LLM-based check.
    If the LLM is sufficiently confident (confidence >= threshold),
    its result is returned along with any reference links.
    Otherwise, the system falls back to using Google Fact Check Tools.
    """
    def __init__(self, openai_api_key: str, google_api_key: str, logger):
        self.llm_source = LLMFactCheckAPI(openai_api_key)
        self.google_source = GoogleFactCheckAPI(google_api_key)
        self.logger = logger
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
            return await self._check_google(claim)

    async def check_facts(self, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check a list of claims using the fact checking pipeline.
        Returns aggregated results and summary.
        """
        if not claims:
            return {
                "aggregated_results": [],
                "summary": {"status": "no_claims_to_check"}
            }

        processing_times = {}
        results = []

        for claim in claims:
            claim_text = claim["text"] if isinstance(claim, dict) else str(claim)
            start_time = time.time()
            
            # Process the claim
            try:
                result = await self.check_fact(claim_text)
                processing_time = time.time() - start_time
                processing_times[claim_text] = processing_time
                
                # Add timestamps to result if available
                if isinstance(claim, dict):
                    result["start_time"] = claim.get("start_time")
                    result["end_time"] = claim.get("end_time")
                
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error processing claim: {e}")
                results.append({
                    "claim": claim_text,
                    "status": "error",
                    "error": str(e)
                })

        # Calculate summary statistics
        total_time = sum(processing_times.values())
        avg_time = total_time / len(claims) if claims else 0
        
        summary = {
            "total_claims": len(claims),
            "total_processing_time": total_time,
            "average_processing_time": avg_time,
            "status": "completed"
        }

        return {
            "aggregated_results": results,
            "summary": summary
        }