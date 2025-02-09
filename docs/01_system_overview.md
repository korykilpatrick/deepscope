# 1. System Overview

## High-Level Architecture
This AI-powered financial fact-checking service ingests textual transcripts from Firebase, identifies falsifiable financial claims, and verifies each claim against trusted data sources. It comprises modules for claim extraction, claim verification, and result dissemination. The pipeline uses Python, LangChain, FastAPI, and Firebase:

1. **Firebase Trigger/Intake**  
   - Detect new or updated transcripts in Firebase.
   - Fetch the text for further processing.

2. **Claim Extraction & Categorization**  
   - Use NLP to identify potential financial claims (stock prices, earnings, etc.).
   - Tag each claim by type to decide which data sources to query.

3. **Verification Against Multiple APIs**  
   - Gather evidence from external sources (e.g. EDGAR, Alpha Vantage).
   - Apply consensus logic to arrive at a true/false verdict with confidence scores.

4. **Result Storage & API**  
   - Store fact-check outcomes in Firebase.
   - Expose the data through FastAPI endpoints for client consumption.

## End-to-End Data Flow
1. **Transcript Added** – A new transcript is placed in Firebase.
2. **Ingestion** – The system reads the transcript text.
3. **Claim Extraction** – NLP identifies check-worthy statements.
4. **Verification** – Each claim is checked against relevant financial APIs.
5. **Consensus** – The system combines all sources to assign a truth label.
6. **Output** – Final results (claims + verdicts) are stored in Firebase and made available via API.

## Primary Functionalities
- **Automated Claim Detection**: Identifies factual statements specific to finance.
- **Multi-Source Fact Verification**: Cross-references multiple data sources to determine veracity.
- **Consensus Scoring**: Uses evidence weighting or majority votes to finalize verdicts.
- **Results API**: Exposes fact-check outcomes for external integrations.
- **Depth over Speed**: Prioritizes comprehensive checks over real-time performance.
