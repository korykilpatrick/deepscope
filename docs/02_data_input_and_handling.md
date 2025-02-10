# 2. Data Input & Handling

## Transcript Ingestion from Firebase
- Store transcripts in Firebase (Firestore or Cloud Storage).
- Trigger the processing pipeline when a new transcript is created or updated.
  - Could use a **Firebase Cloud Function** to call a FastAPI endpoint.
  - Or periodically poll Firebase for new transcripts.

## Storage and Preprocessing
- Retrieve raw text, clean/segment it (remove extraneous characters, timestamps, etc.).
- Maintain transcript metadata (ID, timestamp, status).
- Optionally queue transcripts for asynchronous processing to avoid blocking HTTP calls.

## Processing Pipeline
1. **Trigger/Fetch**  
   - Detect or poll for new transcripts.
   - Download and clean the text payload.

2. **Queue (Optional)**  
   - Add transcript references to a task queue (e.g. Celery, Redis).

3. **Preprocess Text**  
   - Tokenize or split into sentences, remove noise, unify formatting.

4. **Ready for Extraction**  
   - Pass cleaned text into the claim extraction step.

## Error Handling
- Log failures (fetching, parsing) and mark transcript as "failed."
- Update Firebase with status transitions (e.g., "in_progress", "processed").