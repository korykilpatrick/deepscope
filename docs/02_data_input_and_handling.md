# 2. Data Input & Handling

## Transcript Ingestion from Firebase
- Store transcripts in Firebase (Firestore or Cloud Storage).
- Trigger the processing pipeline when a new transcript is created:
  - Either use a **Firebase Cloud Function** calling a FastAPI endpoint.
  - Or have the FastAPI service poll/query for new transcripts.

## Storage and Preprocessing
- Retrieve raw text and clean/segment it (remove extraneous characters, split into sentences).
- Maintain each transcript’s metadata (ID, timestamp, etc.).
- Optionally queue transcripts for asynchronous processing to avoid blocking the main thread.

## Processing Pipeline
1. **Trigger/Fetch**  
   - Detect or poll for new transcripts.
   - Download the text payload.

2. **Queue (Optional)**  
   - Add the transcript ID to a local or external task queue.

3. **Preprocess Text**  
   - Tokenize into sentences, remove noise, ensure consistent formatting.

4. **Ready for Extraction**  
   - Pass cleaned text to the claim extraction module.

## Error Handling
- If fetching or parsing fails, log the issue and mark transcript as "failed" without blocking subsequent tasks.
- Update transcript status in Firebase (e.g., "in_progress", "processed") to reflect pipeline progress.
