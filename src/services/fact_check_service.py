import asyncio
import time
import json
import httpx
from random import uniform
from typing import List, Dict, Any, Protocol
from datetime import datetime

from openai import OpenAI  # Use the new OpenAI client interface

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
                    rev_copy = rev.copy()  # Preserve all metadata
                    rev_copy["interpreted_rating"] = self._interpret_rating(rev.get("textualRating", ""))
                    all_reviews.append(rev_copy)
                    if rev_copy["interpreted_rating"] == "match":
                        match_count += 1
                    elif rev_copy["interpreted_rating"] == "mismatch":
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
                "evidence": {"claim_reviews": all_reviews, "raw_data": data},
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
            "Return your response as a JSON object with keys 'verdict' ('true', 'false', 'uncertain'), "
            "'confidence' (0 to 1), 'explanation', and 'reference_links' (array of URLs). "
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
    Hybrid fact checker that now calls BOTH the LLM and Google Fact Checker,
    returning separate confidences and preserving all Google API metadata.
    """
    def __init__(self, openai_api_key: str, google_api_key: str, logger):
        self.llm_source = LLMFactCheckAPI(openai_api_key)
        self.google_source = GoogleFactCheckAPI(google_api_key)
        self.logger = logger

    async def _check_llm(self, claim: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.llm_source.check_claim, claim)

    async def _check_google(self, claim: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.google_source.check_claim, claim)

    async def check_fact(self, claim: str) -> Dict[str, Any]:
        # Always call LLM first, then Google
        llm_res = await self._check_llm(claim)
        google_res = await self._check_google(claim)

        llm_conf = llm_res.get("evidence", {}).get("confidence", 0.0)
        google_verification = google_res.get("verification", "no_data")
        if google_verification == "match":
            google_conf = 1.0
        elif google_verification == "mismatch":
            google_conf = 1.0
        elif google_verification == "conflicting":
            google_conf = 0.5
        else:
            google_conf = 0.0

        google_evidence = google_res.get("evidence", {})

        return {
            "claim_text": claim,
            "llm_verification": llm_res.get("verification", "no_data"),
            "llm_confidence": llm_conf,
            "llm_explanation": llm_res.get("evidence", {}).get("explanation", ""),
            "llm_reference_links": llm_res.get("evidence", {}).get("reference_links", []),
            "google_verification": google_verification,
            "google_confidence": google_conf,
            "google_evidence": google_evidence,  # full metadata including raw_data and claim_reviews
            "google_sources": google_evidence.get("claim_reviews", [])
        }

    async def check_facts(self, claims: List[str]) -> List[Dict[str, Any]]:
        results = []
        for claim in claims:
            try:
                result = await self.check_fact(claim)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error processing claim: {e}")
                results.append({
                    "claim_text": claim,
                    "llm_verification": "no_data",
                    "llm_confidence": 0.0,
                    "google_verification": "no_data",
                    "google_confidence": 0.0,
                    "sources": [],
                    "error": str(e)
                })
        return results