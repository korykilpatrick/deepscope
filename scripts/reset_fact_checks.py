#!/usr/bin/env python3
import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.dependencies import get_firebase_db

# Get the database instance from dependencies
db = get_firebase_db()

def delete_collection(coll_ref, batch_size=10):
    docs = list(coll_ref.limit(batch_size).stream())
    if not docs:
        return
    for doc in docs:
        # Delete any nested subcollections
        for subcoll in doc.reference.collections():
            delete_collection(subcoll, batch_size)
        doc.reference.delete()
    delete_collection(coll_ref, batch_size)

def reset_video_status(video_id):
    """Reset a video's status to pending"""
    video_ref = db.collection('videos').document(video_id)
    video_ref.update({"status": "pending"})
    print(f"Reset status to pending for video: {video_id}")

def reset_fact_check_results():
    # Get all videos first
    videos = db.collection('videos').stream()
    video_ids = [doc.id for doc in videos]
    
    # Reset fact check results
    for video_id in video_ids:
        # Reset the video status to pending
        reset_video_status(video_id)
        
        # Delete fact check results if they exist
        fact_check_ref = db.collection('fact_checks').document(video_id)
        if fact_check_ref.get().exists:
            subcoll = fact_check_ref.collection('fact_check_results')
            delete_collection(subcoll)
            print(f"Deleted fact check results for video: {video_id}")

if __name__ == '__main__':
    reset_fact_check_results()
    print("All videos have been reset to pending status and fact check results have been cleared.")