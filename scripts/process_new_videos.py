#!/usr/bin/env python3
import requests
import time

BASE_URL = "http://localhost:8000"

def get_videos():
    r = requests.get(f"{BASE_URL}/videos")
    r.raise_for_status()
    return r.json()

def process_video(video_id):
    r = requests.post(f"{BASE_URL}/videos/{video_id}/process")
    r.raise_for_status()
    return r.json()

def main():
    videos = get_videos()
    for video in videos:
        if video.get("status") not in ["processed", "in_progress"]:
            vid = video["video_id"]
            print(f"Processing video: {vid}")
            try:
                result = process_video(vid)
                print(f"Response for {vid}: {result}")
            except Exception as e:
                print(f"Error processing {vid}: {e}")
            time.sleep(5)  # throttle calls

if __name__ == "__main__":
    main()