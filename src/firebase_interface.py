import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()  # loads variables from .env

# Use the environment variable to locate your credentials file.
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

db = firestore.client()

def get_transcript(transcript_id: str):
    doc_ref = db.collection('transcripts').document(transcript_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def update_transcript_status(transcript_id: str, status: str):
    doc_ref = db.collection('transcripts').document(transcript_id)
    doc_ref.update({"status": status})