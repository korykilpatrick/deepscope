# 6. Implementation Details

## Technology Stack
- **Python** for main logic.
- **FastAPI** for the REST API.
- **LangChain** (optional) for LLM-based claim extraction and verification.
- **Firebase** for transcript storage and pipeline status.

## Service Architecture
- **Modules**:
  - `firebase_interface.py` – CRUD interactions with Firebase.
  - `claim_extractor.py` – NLP or LLM-based claim detection.
  - `factchecker.py` – Functions to call external fact-check APIs or run LLM verification.
  - `verdict_aggregator.py` – Aggregates multiple checks into a final verdict.
  - `api_routes.py` – FastAPI endpoints for ingestion and retrieval.

## Firebase Integration
- Use Admin SDK or Cloud Functions:
  - On new transcript, either call the pipeline or mark it “needs_check.”
- Store final results in `fact_check_results` subcollections or a dedicated collection.

## Asynchronous Processing
- **FastAPI** + `asyncio` to handle multiple claims concurrently.
- Background tasks to avoid blocking requests for large transcripts.

## Error Handling & Retries
- Gracefully handle missing data or rate-limits from external APIs.
- Use logging for debugging and skip failing sources rather than abort the entire pipeline.

## Example Processing Flow
1. **Ingestion**: Transcripts from Firebase queued for processing.
2. **Claim Extraction**: `claim_extractor` finds potential factual statements.
3. **Parallel Checks**: `factchecker` queries multiple external APIs + LLM verification.
4. **Aggregation**: `verdict_aggregator` merges results to yield a final verdict.
5. **Store & Return**: Store all outcomes in Firebase; API endpoints expose them.