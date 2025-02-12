"""
Pydantic models for fact-checking data structures.

Example Usage:
    ```python
    # Create an Evidence instance
    evidence = Evidence(
        summary="Multiple scientific studies confirm this claim",
        reference_links=["https://example.com/study1", "https://example.com/study2"],
        last_updated=datetime.utcnow()
    )

    # Create a GPT-4 fact check source
    gpt4_source = FactCheckSource(
        source_id="gpt4_1",
        source_name="GPT-4",
        source_type="llm",
        verification="match",
        confidence=0.92,
        evidence=evidence
    )

    # Create a Google Fact Check Tools source
    google_source = FactCheckSource(
        source_id="google_1",
        source_name="Google Fact Check Tools",
        source_type="api",
        verification="match",
        confidence=1.0,
        evidence=Evidence(
            summary="Three fact-checking organizations have verified this claim",
            reference_links=["https://factcheck.org/claim123"],
            last_updated=datetime.utcnow()
        )
    )

    # Validate and get dictionary representation
    source_dict = gpt4_source.model_dump()

    # Access fields with type safety
    if gpt4_source.verification == "match" and gpt4_source.confidence > 0.8:
        print(f"High confidence match from {gpt4_source.source_name}")
    ```
"""

from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field, HttpUrl

class Evidence(BaseModel):
    """Evidence supporting a fact check result.
    
    This class represents the supporting evidence for a fact check verification,
    including a summary explanation, reference links, and timestamp.

    Attributes:
        summary: A human-readable explanation of the fact check result
        reference_links: A list of URLs to supporting evidence
        last_updated: Timestamp of when the verification was performed

    Example:
        ```python
        evidence = Evidence(
            summary="Scientific consensus supports this claim based on multiple studies",
            reference_links=["https://science.org/study1"],
            last_updated=datetime.utcnow()
        )
        ```
    """
    summary: str = Field(..., description="Human-readable explanation/summary of the fact check")
    reference_links: List[HttpUrl] = Field(default_factory=list, description="List of supporting URLs")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when this verification was performed")

class FactCheckSource(BaseModel):
    """A single fact check source result.
    
    This class represents the result from a single fact-checking source,
    whether it's an LLM or an external API. It includes the source's
    verification, confidence, and supporting evidence.

    Attributes:
        source_id: Unique identifier for this source result
        source_name: Name of the source (e.g., 'GPT-4', 'Google Fact Check Tools')
        source_type: Type of source - either 'llm' or 'api'
        verification: The verification result - 'match', 'mismatch', 'no_data', or 'conflicting'
        confidence: Confidence score between 0 and 1
        evidence: Supporting evidence for the verification

    Example:
        ```python
        source = FactCheckSource(
            source_id="gpt4_1",
            source_name="GPT-4",
            source_type="llm",
            verification="match",
            confidence=0.92,
            evidence=Evidence(
                summary="Analysis confirms this claim",
                reference_links=["https://example.com/evidence"],
                last_updated=datetime.utcnow()
            )
        )
        ```
    """
    source_id: str = Field(..., description="Unique identifier for this source result")
    source_name: str = Field(..., description="Name of the source (e.g., 'GPT-4', 'Google Fact Check Tools')")
    source_type: Literal["llm", "api"] = Field(..., description="Type of the source")
    verification: Literal["match", "mismatch", "no_data", "conflicting"] = Field(..., description="Verification result")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    evidence: Evidence = Field(..., description="Evidence supporting the verification") 