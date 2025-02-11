import unittest
import sys
import os
import asyncio
import json
from typing import Dict, Any

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from factchecker import GoogleFactCheckAPI, FactChecker, check_fact
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TestFactChecker(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.assertTrue(self.api_key is not None, "GOOGLE_API_KEY not found in environment variables")
        self.google_api = GoogleFactCheckAPI()
        self.fact_checker = FactChecker()

    def assertValidFactCheckResponse(self, result: Dict[str, Any], msg: str = ""):
        """Helper method to validate fact check response structure"""
        self.assertIsInstance(result, dict, f"{msg} Result should be a dictionary")
        self.assertIn("source_name", result, f"{msg} Result should have 'source_name'")
        self.assertIn("verification", result, f"{msg} Result should have 'verification'")
        self.assertIn("evidence", result, f"{msg} Result should have 'evidence'")
        self.assertIn("source_url", result, f"{msg} Result should have 'source_url'")
        self.assertIn(result["verification"], ["match", "mismatch", "no_data"], 
                     f"{msg} Verification should be one of: match, mismatch, no_data")

    def test_google_factcheck_direct(self):
        """Test direct Google Fact Check API with a known false claim"""
        test_claim = "The Earth is flat"
        result = self.google_api.check_claim(test_claim)
        print(f"\nTesting claim: '{test_claim}'")
        print("Result:", json.dumps(result, indent=2))
        print("--------------------------------")
        self.assertValidFactCheckResponse(result, "Direct Google Fact Check:")
        
    def test_google_factcheck_true_claim(self):
        """Test with a known true claim"""
        test_claim = "The Earth orbits around the Sun"
        result = self.google_api.check_claim(test_claim)
        print(f"\nTesting claim: '{test_claim}'")
        print("Result:", json.dumps(result, indent=2))
        print("--------------------------------")
        self.assertValidFactCheckResponse(result, "True claim check:")

    def test_google_factcheck_ambiguous_claim(self):
        """Test with an ambiguous or complex claim"""
        test_claim = "Climate change is causing sea levels to rise"
        result = self.google_api.check_claim(test_claim)
        print(f"\nTesting claim: '{test_claim}'")
        print("Result:", json.dumps(result, indent=2))
        print("--------------------------------")
        self.assertValidFactCheckResponse(result, "Ambiguous claim check:")

    async def async_test_full_pipeline(self):
        """Test the complete fact-checking pipeline"""
        test_claim = "The Earth is flat"
        result = await check_fact(test_claim)
        
        # Validate overall structure
        self.assertIsInstance(result, dict)
        self.assertIn("claim_text", result)
        self.assertIn("final_verdict", result)
        self.assertIn("confidence", result)
        self.assertIn("checked_sources", result)
        
        # Validate checked sources
        self.assertIsInstance(result["checked_sources"], list)
        self.assertGreater(len(result["checked_sources"]), 0)
        
        # Validate each source
        for source in result["checked_sources"]:
            self.assertValidFactCheckResponse(source, f"Source check for {source.get('source_name', 'unknown')}:")

    def test_full_pipeline(self):
        """Wrapper to run async test"""
        asyncio.run(self.async_test_full_pipeline())

if __name__ == '__main__':
    unittest.main() 