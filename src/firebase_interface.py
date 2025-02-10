import os
import re
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, Dict, Any, List

load_dotenv()  # loads variables from .env

# Use the environment variable to locate your credentials file.
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

db = firestore.client()

def clean_transcript_text(text: str) -> str:
    """
    Clean the transcript text by removing timestamps and extra whitespace.
    
    Args:
        text: Raw transcript text with timestamps
        
    Returns:
        Cleaned text with just the spoken content
    """
    # Remove timestamp lines (HH:MM:SS,MMM --> HH:MM:SS,MMM)
    text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\n', '', text)
    
    # Remove empty lines and \r characters
    text = re.sub(r'\r', '', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    
    # Remove duplicate consecutive phrases (common in subtitles)
    unique_lines = []
    for line in lines:
        if not unique_lines or line != unique_lines[-1]:
            unique_lines.append(line)
    
    # Join into a single clean text
    text = ' '.join(unique_lines)
    
    return text

def get_transcript(transcript_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a transcript from the videos collection.
    
    Args:
        transcript_id: The ID of the video document
        
    Returns:
        Dict containing the transcript data if found, None otherwise
    """
    doc_ref = db.collection('videos').document(transcript_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
        
    data = doc.to_dict()
    if not data or 'transcript' not in data:
        return None
    
    raw_text = data['transcript']
    cleaned_text = clean_transcript_text(raw_text)
        
    return {
        'id': doc.id,
        'text': cleaned_text,
        'raw_text': raw_text,  # Keep the original text just in case
        'timestamp': data.get('timestamp'),
        'status': data.get('status', 'pending')
    }

def update_transcript_status(transcript_id: str, status: str):
    """
    Update the status field of a video document.
    
    Args:
        transcript_id: The ID of the video document
        status: The new status to set
    """
    doc_ref = db.collection('videos').document(transcript_id)
    doc_ref.update({"status": status})

def get_all_videos() -> List[Dict[str, Any]]:
    """
    Retrieve all video documents from the videos collection.
    
    Returns:
        List of dictionaries containing video data
    """
    videos_ref = db.collection('videos')
    docs = videos_ref.stream()
    
    videos = []
    for doc in docs:
        data = doc.to_dict()
        if data:
            video = {
                'video_id': doc.id,
                'title': data.get('title', ''),
                'status': data.get('status', 'pending'),
                'transcript': data.get('transcript', ''),
                'created_at': data.get('timestamp', '')
            }
            videos.append(video)
    
    return videos