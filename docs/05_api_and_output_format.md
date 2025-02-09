# 5. API & Output Format

## API Endpoints
- `GET /transcripts/{id}/claims`
  - Returns all extracted claims and their verifications for a given transcript.
  - If processing is incomplete, returns status or partial results.
- (Optional) `GET /claims/{claim_id}`
  - Retrieves fact-check outcome for a specific claim.
- (Optional) `POST /check`
  - Accepts raw text or a single claim; returns immediate verification results (suitable for ad-hoc checks).

## Response Schema
Each claim returns:
- **claim_text**: The exact statement or sentence.
- **category**: E.g., “Market Data”, “Company Financials.”
- **result**: “true,” “false,” “unverified,” or “conflicting.”
- **confidence_score**: Numeric or qualitative measure (e.g., 0.0–1.0).
- **checked_sources**: Array of objects detailing evidence from each data source:
  - `source_name` (e.g., “AlphaVantage”)
  - `verification` (match / mismatch / no data)
  - `evidence` (e.g., the numeric figure or a fact-check result)
  - `source_url` (link to underlying evidence if available)
- **explanation**: Concise textual summary of how the verdict was reached.

## Example
```json
{
  "transcript_id": "abc123",
  "claims": [
    {
      "claim_text": "ACME Corp's Q1 2023 revenue was $500 million.",
      "category": "Company Financials",
      "result": "false",
      "confidence_score": 0.9,
      "checked_sources": [
        {
          "source_name": "SEC EDGAR",
          "verification": "mismatch",
          "evidence": "Reported $480 million",
          "source_url": "https://.../10Q"
        }
      ],
      "explanation": "EDGAR shows $480M, so the claim is false."
    }
  ]
}
