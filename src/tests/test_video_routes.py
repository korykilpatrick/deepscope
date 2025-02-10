import unittest
import sys
import os

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.main import app
from fastapi.testclient import TestClient

class TestVideoRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_videos(self):
        """Test that we can get videos and they have the required fields"""
        response = self.client.get("/videos")
        self.assertEqual(response.status_code, 200)
        videos = response.json()
        
        # Check we got a list of videos
        self.assertIsInstance(videos, list)
        self.assertGreater(len(videos), 0, "Should have at least one video in the collection")
        
        # Check each video has the required fields
        for video in videos:
            # Required fields for our project
            self.assertIn("video_id", video, "Video should have video_id")
            self.assertIn("transcript", video, "Video should have transcript")
            self.assertIn("status", video, "Video should have status")
            
            # Check data types
            self.assertIsInstance(video["video_id"], str)
            self.assertIsInstance(video["transcript"], str)
            self.assertIsInstance(video["status"], str)
            
            # Status should be either pending or processed
            self.assertIn(video["status"], ["pending", "processed"], 
                         f"Status should be 'pending' or 'processed', got {video['status']}")

if __name__ == '__main__':
    unittest.main() 