# 5. API & Output Format

## API Endpoints
- `GET /transcripts/{id}/claims`
  - Returns extracted claims and verification results for a transcript.
  - If processing is incomplete, returns partial info or status.

- `POST /check`
  - Accepts raw text or a single claim and returns immediate verification results (good for ad-hoc checks).

## Response Schema
- **claim_text**: Original statement or sentence.
- **category**: (optional) The domain label if used.
- **result**: “true,” “false,” “unverified,” or “conflicting.”
- **confidence_score**: Numeric measure (0.0–1.0) or a qualitative measure.
- **checked_sources**: Array of source-level details:
  - `source_name`
  - `verification` (“match,” “mismatch,” “no_data,” etc.)
  - `evidence` (e.g., a snippet or summary from the source)
  - `source_url` (if available)
- **explanation**: Short summary describing the reasoning.

## Example
```json
{
  "transcript_id": "abc123",
  "claims": [
    {
      "claim_text": "Water boils at 105°C at sea level.",
      "result": "false",
      "confidence_score": 0.9,
      "checked_sources": [
        {
          "source_name": "Generic FactCheck API",
          "verification": "mismatch",
          "evidence": "Data indicates 100°C is standard.",
          "source_url": "https://example.com/factchecks/water-boiling"
        }
      ],
      "explanation": "Evidence shows the boiling point is typically 100°C."
    }
  ]
}