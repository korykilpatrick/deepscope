# 4. Truth Verification Pipeline

## Integrating Multiple Fact-Checking Methods
- **LLM-Based Verification**: Prompt a large language model to analyze a claim and check it against known knowledge or reasoning.
- **External Fact-Check APIs**: For example:
  - [Google Fact Check Tools API](https://toolbox.google.com/factcheck)
  - [Factiverse API](https://factiverse.no)
  - [Parafact](https://parafact.ai)
  - Or other specialized datasets (e.g., custom knowledge bases).

## Consensus Logic for Truth Scoring
1. **Source-by-Source Check**  
   - Each API returns a partial verdict (supported, refuted, or unknown).
   - LLM might output a probability score or “true/false/inconclusive.”

2. **Weighted or Majority Vote**  
   - Aggregate results to assign a final label (e.g., “true,” “false,” “unverified/conflicting”).

3. **Handling Missing/Conflicting Info**
   - If no sources have data, label the claim “unverified.”
   - If some sources confirm and others refute, mark “conflicting” or low confidence.

## Example
- Claim: “Water boils at 105°C at sea level.”
- LLM or fact-check sources show standard boiling point is ~100°C => verdict “false,” confidence high.