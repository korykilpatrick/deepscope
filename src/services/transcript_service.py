from typing import Optional, Dict, Any, List
from google.cloud.firestore import Client
from ..logging_config import get_logger
import re

logger = get_logger()

class TranscriptService:
    """
    Handles transcript retrieval, cleaning, and status updates in Firebase.
    """

    def __init__(self, db: Client):
        self.db = db

    def parse_srt_segments(self, raw_text: str) -> List[Dict[str, Any]]:
        pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}|\Z)'
        matches = re.findall(pattern, raw_text, flags=re.DOTALL)
        segments = []
        for match in matches:
            index, start_time, end_time, content = match
            content = re.sub(r'\r|\n+', ' ', content).strip()
            segments.append({
                "index": int(index),
                "start": start_time,
                "end": end_time,
                "text": content
            })
        return segments

    def clean_transcript_text(self, text: str) -> str:
        text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\n', '', text)
        text = re.sub(r'\r', '', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        unique_lines = []
        for line in lines:
            if not unique_lines or line != unique_lines[-1]:
                unique_lines.append(line)
        return ' '.join(unique_lines)

    def get_transcript(self, transcript_id: str) -> Optional[Dict[str, Any]]:
        doc_ref = self.db.collection('videos').document(transcript_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if not data or 'transcript' not in data:
            return None

        raw_text = data['transcript']
        segments = self.parse_srt_segments(raw_text)
        joined_text = ' '.join([seg['text'] for seg in segments]) if segments else self.clean_transcript_text(raw_text)
        return {
            'id': doc.id,
            'segments': segments,
            'text': joined_text,
            'raw_text': raw_text,
            'timestamp': data.get('timestamp'),
            'status': data.get('status', 'pending')
        }

    def update_transcript_status(self, transcript_id: str, status: str):
        doc_ref = self.db.collection('videos').document(transcript_id)
        doc_ref.update({"status": status})

    def get_all_videos(self) -> List[Dict[str, Any]]:
        videos_ref = self.db.collection('videos')
        docs = videos_ref.stream()
        videos = []
        for doc in docs:
            data = doc.to_dict()
            if data:
                videos.append({
                    'video_id': doc.id,
                    'title': data.get('title', ''),
                    'status': data.get('status', 'pending'),
                    'transcript': data.get('transcript', ''),
                    'created_at': data.get('timestamp', '')
                })
        return videos

    def store_fact_check_results(self, video_id: str, claims: List[Dict[str, Any]]):
        """
        Stores each fact check result as a doc in the 'fact_check_results' subcollection.
        Then stores the 'sources' array as its own subcollection for that doc.
        """
        doc_ref = self.db.collection('videos').document(video_id)
        for i, claim_data in enumerate(claims):
            sources = claim_data.pop("sources", [])
            claim_ref = doc_ref.collection('fact_check_results').document(str(i))
            claim_ref.set(claim_data)
            for j, source_data in enumerate(sources):
                claim_ref.collection('sources').document(str(j)).set(source_data)