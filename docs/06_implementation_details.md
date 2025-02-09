# 6. Implementation Details

## Technology Stack
- **Python** for core logic.
- **FastAPI** for RESTful endpoints.
- **LangChain** for LLM-based claim extraction/explanation.
- **Firebase** for transcript storage and result updates.

## Service Architecture
- **Module Breakdown**:
  - `firebase_interface.py` – reading/writing transcripts & results from/to Firebase.
  - `claim_extractor.py` – NLP logic (may use LangChain or a local model).
  - `factchecker.py` – API call functions (EDGAR, Alpha Vantage, etc.).
  - `verdict_aggregator.py` – consensus logic for final label/confidence.
  - `api_routes.py` – FastAPI routes, orchestrating the pipeline.

- **LangChain Integration**:
  - LLM-based claim identification: prompt-based approach to parse transcripts into factual claims.
  - Optional: use an Agent to decide which sources to call for each claim.

## Firebase Integration
- Use the Admin SDK or a Cloud Function trigger:
  - On new transcript: call the fact-check endpoint in FastAPI or update a “needs_check” field.
  - Once processed, store results in a subcollection like `transcripts/{id}/fact_check_results`.

## Asynchronous Processing
- **FastAPI** + `asyncio` for concurrent HTTP requests to external APIs.
- Potential background tasks to handle large transcripts, preventing timeouts.

## Error Handling & Retries
- If an external API fails or times out, mark that source as “no data.”
- Implement limited retries for transient network issues or rate limits.
- Log all errors for debugging without blocking the entire pipeline.

## Example Processing Flow
1. **Ingestion**: Transcripts from Firebase are queued.
2. **Claim Extraction**: Use `claim_extractor.py` to identify claims.
3. **Parallel Fact-Check**: For each claim, gather data from EDGAR/AlphaVantage/etc. concurrently.
4. **Aggregate**: `verdict_aggregator.py` merges evidence into a final verdict.
5. **Store & Return**: Save outcome in Firebase and provide it to the user via `GET /transcripts/{id}/claims`.
