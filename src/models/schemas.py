"""
Pydantic models for fact-checking data structures.
"""

from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field, HttpUrl

class Evidence(BaseModel):
    """Evidence supporting a fact check result."""
    summary: str = Field(..., description="Human-readable explanation/summary of the fact check")
    reference_links: List[HttpUrl] = Field(default_factory=list, description="List of supporting URLs")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when this verification was performed")

class FactCheckSource(BaseModel):
    """A single fact check source result."""
    source_id: str = Field(..., description="Unique identifier for this source result")
    source_name: str = Field(..., description="Name of the source (e.g., 'GPT-4', 'Google Fact Check Tools')")
    source_type: Literal["llm", "api"] = Field(..., description="Type of the source")
    verification: Literal["match", "mismatch", "no_data", "conflicting"] = Field(..., description="Verification result")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    evidence: Evidence = Field(..., description="Evidence supporting the verification") 