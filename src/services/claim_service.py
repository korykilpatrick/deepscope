from datetime import datetime
from typing import List, Dict, Any
from ..chains.base import FullFactCheckingChain
from ..logging_config import get_logger

logger = get_logger()

class ClaimService:
    """
    Coordinates the extraction and verification pipeline for transcripts or raw text.
    """

    def __init__(self, chain: FullFactCheckingChain):
        self.chain = chain

    async def process_text(self, text: str) -> Dict[str, Any]:
        """
        Executes the full pipeline asynchronously using the chain.
        """
        if not text.strip():
            return {"claims": [], "verdicts": [], "final_result": {"status": "no_text"}}
        result = await self.chain.ainvoke({"text": text})
        return result