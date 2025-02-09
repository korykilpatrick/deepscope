# 4. Truth Verification Pipeline

## Integrating Multiple Fact-Checking APIs
- **Google Fact Check API**: Checks if any reputable fact-checking source has already assessed a similar claim.
- **SEC EDGAR**: Compares company financial statements directly from official filings.
- **Alpha Vantage**: Provides low-cost/free stock prices and market data.
- (Optional) **Bloomberg / FactSet**: More comprehensive data for paying enterprise customers.
- For macro stats, consider FRED or other official government data APIs.

## Consensus Logic for Truth Scoring
1. **Source-by-Source Verification**  
   - Each API returns numeric data (e.g., revenue amount) or a boolean verdict (true/false).
   - If an API can’t find relevant data, mark it “no data.”

2. **Majority Vote or Weighted Scoring**  
   - Tally true/false from multiple sources.
   - If sources conflict, label the claim “conflicting evidence” or “low confidence.”

3. **Handling Missing/Conflicting Information**  
   - If no data is found, consider the claim “unverified.”
   - If direct contradictions exist, mark the claim “needs review” or “conflicting.”

## Example
- Claim: “ACME’s Q1 revenue was $500M.”
- EDGAR indicates $480M. FactSet also reports $480M.  
- Both sources say mismatch => final verdict “false,” with a high confidence score.
