import asyncio
import time
import json
import httpx
from random import uniform
from typing import List, Dict, Any, Protocol
from datetime import datetime

from openai import OpenAI  # Use the new OpenAI client interface
from ..models.schemas import Evidence, FactCheckSource as FactCheckResult  # Import new models

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
    """GPT-4 based fact checker using the OpenAI API interface."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not provided")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4"  # Store the model name for reference

    def check_claim(self, claim: str) -> Dict[str, Any]:
        system_prompt = """You are a reliable fact-checking assistant. Your task is to evaluate claims for truthfulness and return results in a specific format.

For each claim, you must return a JSON object with the following structure that matches our Pydantic models:

{
    "verification": string,  // Must be one of: "match" (true), "mismatch" (false), "no_data" (uncertain), "conflicting"
    "confidence": float,    // Value between 0 and 1
    "evidence": {
        "summary": string,  // Detailed explanation of your verification
        "reference_links": [string],  // List of URLs to supporting evidence
    }
}

Guidelines:
- verification: Use "match" for true claims, "mismatch" for false claims, "no_data" for uncertain claims
- confidence: Express your certainty level (0.9+ for very certain, 0.5-0.8 for moderately certain, <0.5 for uncertain)
- summary: Provide a clear, detailed explanation of your reasoning
- reference_links: Include relevant, authoritative sources when possible

Example responses:

1. For a verified true claim:
{
    "verification": "match",
    "confidence": 0.95,
    "evidence": {
        "summary": "This claim is verified true based on multiple reliable sources. The World Health Organization's 2023 report confirms that regular exercise reduces the risk of cardiovascular disease by 30-40%.",
        "reference_links": [
            "https://www.who.int/publications/health-benefits-exercise-2023",
            "https://www.ncbi.nlm.nih.gov/studies/exercise-benefits"
        ]
    }
}

2. For a verified false claim:
{
    "verification": "mismatch",
    "confidence": 0.98,
    "evidence": {
        "summary": "This claim is demonstrably false. NASA and multiple space agencies have provided extensive photographic and scientific evidence that the Earth is spherical, not flat.",
        "reference_links": [
            "https://nasa.gov/earth-observations",
            "https://science.nasa.gov/earth-shape-evidence"
        ]
    }
}

3. For an uncertain or unverifiable claim:
{
    "verification": "no_data",
    "confidence": 0.3,
    "evidence": {
        "summary": "There is insufficient evidence to verify or refute this claim. While some preliminary studies exist, they are not conclusive and more research is needed.",
        "reference_links": []
    }
}

4. For a claim with conflicting evidence:
{
    "verification": "conflicting",
    "confidence": 0.5,
    "evidence": {
        "summary": "There are credible sources supporting and refuting this claim. Study A suggests the treatment is effective, while Study B shows no significant benefits. More research is needed to resolve this contradiction.",
        "reference_links": [
            "https://medical-journal.com/study-a-results",
            "https://health-research.org/study-b-findings"
        ]
    }
}"""

        user_prompt = f"Please evaluate this claim and provide your assessment in the specified JSON format:\n\nClaim: {claim}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            message_content = response.choices[0].message.content
            result_json = json.loads(message_content)
            
            # Ensure the response matches our expected format
            if not all(k in result_json for k in ["verification", "confidence", "evidence"]):
                raise ValueError("Invalid response format from LLM")
            if not all(k in result_json["evidence"] for k in ["summary", "reference_links"]):
                raise ValueError("Invalid evidence format from LLM")
                
            return {
                "source_name": self.model,  # Just return the model name
                "verification": result_json["verification"],
                "evidence": {
                    "explanation": result_json["evidence"]["summary"],
                    "reference_links": result_json["evidence"]["reference_links"],
                    "confidence": result_json["confidence"]
                }
            }
        except Exception as e:
            return {
                "source_name": self.model,  # Just return the model name
                "verification": "no_data",
                "evidence": {
                    "explanation": f"Error processing with {self.model}: {str(e)}",
                    "reference_links": [],
                    "confidence": 0.0
                }
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

        # Get the model name from the LLM source instance
        model_name = self.llm_source.model.replace("-", "").lower()  # e.g., "gpt4" from "gpt-4"
        
        # Create LLM source result using Pydantic model
        llm_evidence = Evidence(
            summary=llm_res.get("evidence", {}).get("explanation", ""),
            reference_links=llm_res.get("evidence", {}).get("reference_links", []),
            last_updated=datetime.utcnow()
        )
        
        llm_source = FactCheckResult(
            source_id=f"{model_name}_1",
            source_name=llm_res.get("source_name", f"{model_name.upper()}"),
            source_type="llm",
            verification=llm_res.get("verification", "no_data"),
            confidence=llm_res.get("evidence", {}).get("confidence", 0.0),
            evidence=llm_evidence
        )

        # Create Google source result using Pydantic model
        google_verification = google_res.get("verification", "no_data")
        google_confidence = 1.0 if google_verification in ["match", "mismatch"] else (
            0.5 if google_verification == "conflicting" else 0.0
        )
        
        google_evidence = Evidence(
            summary=str(google_res.get("evidence", {}).get("claim_reviews", [])),
            reference_links=[rev.get("url", "") for rev in google_res.get("evidence", {}).get("claim_reviews", [])],
            last_updated=datetime.utcnow()
        )
        
        google_source = FactCheckResult(
            source_id="google_factcheck_1",
            source_name="Google Fact Check Tools",
            source_type="api",
            verification=google_verification,
            confidence=google_confidence,
            evidence=google_evidence
        )

        # Create individual source results for each Google claim review
        google_review_sources = []
        for i, rev in enumerate(google_res.get("evidence", {}).get("claim_reviews", [])):
            review_evidence = Evidence(
                summary=rev.get("textualRating", ""),
                reference_links=[rev.get("url", "")],
                last_updated=datetime.utcnow()
            )
            
            review_source = FactCheckResult(
                source_id=f"google_review_{i+1}",
                source_name=rev.get("publisher", {}).get("name", "Unknown Publisher"),
                source_type="api",
                verification=rev.get("interpreted_rating", "no_data"),
                confidence=1.0 if rev.get("interpreted_rating") in ["match", "mismatch"] else 0.0,
                evidence=review_evidence
            )
            google_review_sources.append(review_source)

        return {
            "claim_text": claim,
            "sources": [llm_source, google_source] + google_review_sources
        }

    async def check_facts(self, claims: List[str]) -> List[Dict[str, Any]]:
        results = []
        for claim in claims:
            try:
                result = await self.check_fact(claim)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error processing claim: {e}")
                error_evidence = Evidence(
                    summary=f"Error processing claim: {str(e)}",
                    reference_links=[],
                    last_updated=datetime.utcnow()
                )
                error_source = FactCheckResult(
                    source_id="error_1",
                    source_name="Error",
                    source_type="api",  # Using "api" as the source type for errors
                    verification="no_data",
                    confidence=0.0,
                    evidence=error_evidence
                )
                results.append({
                    "claim_text": claim,
                    "sources": [error_source]
                })
        return results