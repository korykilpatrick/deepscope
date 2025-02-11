from langchain.chains.base import Chain
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from abc import ABC

class FactCheckingChain(Chain, ABC):
    """Base chain for fact checking operations"""

    class Config:
        """Configuration for this pydantic object."""
        arbitrary_types_allowed = True

    @property
    def input_keys(self) -> List[str]:
        """Input keys this chain expects."""
        return ["input_text"]

    @property
    def output_keys(self) -> List[str]:
        """Output keys this chain expects."""
        return ["output"]

class ClaimExtractionChain(FactCheckingChain):
    """Chain for extracting claims from text"""

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract claims from input text."""
        from src.claim_extractor import extract_claims

        text = inputs["input_text"]
        claims = extract_claims(text)

        return {"output": claims}

class FactVerificationChain(FactCheckingChain):
    """Chain for verifying claims using fact checking sources"""

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # This chain supports async operations only; use _acall instead.
        raise NotImplementedError("Synchronous call is not implemented. Please use acall() instead.")

    async def _acall(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Verify claims using fact checking sources."""
        from src.factchecker import check_facts

        claims = inputs["input_text"]
        if isinstance(claims, str):
            claims = [claims]

        results = await check_facts(claims)
        return {"output": results}

class VerdictAggregationChain(FactCheckingChain):
    """Chain for aggregating verdicts from multiple sources"""

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate verdicts from multiple sources."""
        from src.verdict_aggregator import aggregate_verdicts

        results = inputs["input_text"]
        aggregated = aggregate_verdicts(results)

        return {"output": aggregated}

class FullFactCheckingChain(Chain):
    """Complete fact checking pipeline combining all chains"""

    claim_extractor: ClaimExtractionChain = Field(default_factory=ClaimExtractionChain)
    fact_verifier: FactVerificationChain = Field(default_factory=FactVerificationChain)
    verdict_aggregator: VerdictAggregationChain = Field(default_factory=VerdictAggregationChain)

    class Config:
        """Configuration for this pydantic object."""
        arbitrary_types_allowed = True

    @property
    def input_keys(self) -> List[str]:
        """Input keys this chain expects."""
        return ["text"]

    @property
    def output_keys(self) -> List[str]:
        """Output keys this chain expects."""
        return ["claims", "verdicts", "final_result"]

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous execution of the fact checking pipeline.
        Note: This will raise a NotImplementedError as the pipeline requires async operations.
        Use acall() instead.
        """
        raise NotImplementedError("This chain only supports async operations. Please use acall() instead.")

    async def _acall(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full fact checking pipeline."""
        # Extract claims
        claims_output = self.claim_extractor({"input_text": inputs["text"]})
        claims = claims_output["output"]

        if not claims:
            return {
                "claims": [],
                "verdicts": [],
                "final_result": {"status": "no_claims_found"}
            }

        # Verify claims asynchronously
        verification_output = await self.fact_verifier._acall({"input_text": claims})
        verdicts = verification_output["output"]

        # Aggregate results
        final_result = self.verdict_aggregator({"input_text": verdicts})["output"]

        return {
            "claims": claims,
            "verdicts": verdicts,
            "final_result": final_result
        }