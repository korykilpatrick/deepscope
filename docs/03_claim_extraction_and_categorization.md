# 3. Claim Extraction & Categorization

## NLP Pipeline for Detecting Financial Claims
- **Sentence-Level Classification**: Use either a machine learning model or a large language model via LangChain to score each sentence’s “check-worthiness.”
- **Heuristics & Entity Recognition**: Identify financial keywords (revenue, EPS, interest rate, etc.) plus numeric data to locate likely factual claims.
- **Output**: A list of extracted statements with relevant metadata (e.g., speaker, sentence index).

## Categorization of Claims
Assign each claim a label based on content:
- **Stock/Market Data**: Ticker symbols, daily price movements, indexes.
- **Company Financials**: Earnings, revenue, profit, cash balances.
- **Macroeconomic Data**: Inflation, interest rates, unemployment.
- **Regulatory/Legal**: SEC approvals, compliance, official announcements.
- **Other Factual Claims**: Catch-all category for anything else numeric or verifiable.

## Purpose of Categorization
- Determines which external APIs to query.
- Ensures domain-specific logic for verifying the statement (e.g., if it’s about stock price, query market data APIs).
- Allows ignoring irrelevant claims or non-falsifiable opinions.
