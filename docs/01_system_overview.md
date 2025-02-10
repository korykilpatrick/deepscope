# 1. System Overview

## High-Level Architecture
This AI-driven fact-checking service ingests textual transcripts from Firebase, identifies falsifiable claims, and verifies each claim against multiple sources (including LLMs and external fact-check APIs). It comprises modules for claim extraction, claim verification, and result dissemination. The pipeline uses Python, LangChain, FastAPI, and Firebase:

1. **Firebase Trigger/Intake**  
   - Detect new or updated transcripts in Firebase.
   - Fetch the text for further processing.

2. **Claim Extraction & Categorization**  
   - Use NLP/LLMs to identify potential factual claims.
   - Assign each claim a category to guide which external checks or APIs to call.

3. **Verification Against Multiple Sources**  
   - Combine LLM reasoning with external fact-check/data APIs.
   - Apply consensus logic to produce a true/false/inconclusive verdict.

4. **Result Storage & API**  
   - Store fact-check outcomes in Firebase.
   - Expose the data via FastAPI endpoints for client consumption.

## End-to-End Data Flow
1. **Transcript Added** – A new transcript is placed in Firebase.
2. **Ingestion** – The system reads the transcript text.
3. **Claim Extraction** – The pipeline identifies check-worthy factual statements.
4. **Verification** – Each claim is checked by LLMs and external APIs.
5. **Consensus** – Aggregates all sources into a truth label with confidence.
6. **Output** – Final results and links/evidence stored and available via REST API.

## Primary Functionalities
- **Automated Claim Detection**: Identifies generic factual statements.
- **Multi-Source Fact Verification**: Leverages LLM-based checks plus external APIs.
- **Consensus Scoring**: Uses weighting or majority rules to finalize verdicts.
- **Results API**: Exposes fact-check outcomes for external integrations.
- **Extensibility**: Designed to handle new data sources or additional modalities (audio/video deepfakes).