# 3. Claim Extraction & Categorization

## NLP Pipeline for Detecting Factual Claims
- **Sentence-Level Analysis**: Use an NLP model or a large language model (via LangChain) to score each sentence’s “check-worthiness.”
- **Optional Heuristics**: Keyword or entity detection to filter out subjective or non-verifiable statements.
- **Output**: A list of extracted statements with metadata (e.g., speaker, sentence index).

## Categorizing Claims
- Can categorize by topic if desired (health, politics, economics, etc.).
- Alternatively, keep a single “generic” category for universal claims.
- This helps route claims to appropriate external APIs or specialized models if you choose domain-specific expansions later.

## Purpose of Categorization
- Decide which external services or data sources are relevant.
- Potentially ignore non-factual statements or opinions.