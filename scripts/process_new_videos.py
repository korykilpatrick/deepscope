#!/usr/bin/env python3
import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def get_videos():
    try:
        r = requests.get(f"{BASE_URL}/videos")
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting videos list: {e}")
        sys.exit(1)

def process_video(video_id):
    try:
        r = requests.post(f"{BASE_URL}/videos/{video_id}/process")
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error processing video {video_id}: {e}")
        return None

def main():
    print("Fetching videos list...")
    videos = get_videos()
    
    if not videos:
        print("No videos found to process")
        return

    for video in videos:
        # Skip videos that are already processed or in progress
        status = video.get("status", "").lower()
        if status in ["processed", "in_progress"]:
            continue
            
        vid = video.get("video_id")
        if not vid:
            print(f"Warning: Found video without ID: {video}")
            continue
            
        print(f"Processing video: {vid} (status: {status})")
        result = process_video(vid)
        
        if result:
            print(f"Successfully queued {vid} for processing")
        
        # Throttle calls
        time.sleep(5)

if __name__ == "__main__":
    main()