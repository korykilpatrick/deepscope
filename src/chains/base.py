from langchain.chains.base import Chain
from pydantic import Field
from typing import Dict, Any, List
from abc import ABC
from ..logging_config import get_logger

logger = get_logger()

class FactCheckingChain(Chain, ABC):
    class Config:
        arbitrary_types_allowed = True

    @property
    def input_keys(self) -> List[str]:
        return ["transcript"]

    @property
    def output_keys(self) -> List[str]:
        return ["output"]

class ClaimExtractionChain(FactCheckingChain):
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        from ..claim_extractor import extract_claims
        text = inputs["transcript"]
        logger.info("ClaimExtractionChain processing input:")
        logger.info(f"First 500 chars: {text[:500]}")
        
        claims = extract_claims(text)
        logger.info(f"Claims extracted: {len(claims)}")
        logger.info(f"Claims: {claims}")
        
        return {"output": claims}

class FactVerificationChain(FactCheckingChain):
    fact_checker: Any = None

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Use async method")

    async def _acall(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        claims = inputs["transcript"]
        if isinstance(claims, str):
            claims = [claims]
        return await self.fact_checker.check_facts(claims)

class VerdictAggregationChain(FactCheckingChain):
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        from ..verdict_aggregator import aggregate_verdicts
        results = inputs["transcript"]
        aggregated = aggregate_verdicts(results)
        return {"output": aggregated}

    async def _acall(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return self._call(inputs)

class FullFactCheckingChain(Chain):
    fact_checker: Any = Field(...)
    claim_extractor: ClaimExtractionChain = Field(default_factory=ClaimExtractionChain)
    fact_verifier: FactVerificationChain = Field(default_factory=FactVerificationChain)
    verdict_aggregator: VerdictAggregationChain = Field(default_factory=VerdictAggregationChain)

    class Config:
        arbitrary_types_allowed = True

    @property
    def input_keys(self) -> List[str]:
        return ["transcript"]

    @property
    def output_keys(self) -> List[str]:
        return ["claims", "verdicts", "final_result"]

    def __init__(self, **data):
        super().__init__(**data)
        # Inject the fact checker into FactVerificationChain
        self.fact_verifier.fact_checker = self.fact_checker

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Use async method")

    async def _acall(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # 1) Extract claims
        logger.info("FullFactCheckingChain starting claim extraction")
        claims_output = self.claim_extractor.invoke({"transcript": inputs["transcript"]})
        claims = claims_output["output"]
        logger.info(f"Claims extracted in full chain: {len(claims)}")
        
        if not claims:
            logger.info("No claims found, returning empty result")
            return {
                "claims": [],
                "verdicts": [],
                "final_result": {"status": "no_claims_found"}
            }
            
        # 2) Verify claims using the fact_verifier
        logger.info("Starting fact verification")
        aggregated = await self.fact_verifier._acall({"transcript": claims})
        logger.info("Fact verification complete")
        
        result = {
            "claims": claims,
            "verdicts": aggregated.get("aggregated_results", []),
            "final_result": aggregated.get("summary", {})
        }
        logger.info(f"Final result: {result}")
        return result