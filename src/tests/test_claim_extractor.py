import unittest
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claim_extractor import extract_claims

class TestClaimExtractor(unittest.TestCase):
    def test_basic_financial_claim(self):
        text = "Apple's revenue increased by 5% in Q2 2024."
        claims = extract_claims(text)
        self.assertEqual(len(claims), 1)
        # Strip punctuation for comparison
        expected = "Apple's revenue increased by 5% in Q2 2024"
        self.assertTrue(any(expected in claim.rstrip('.') for claim in claims))

    def test_non_financial_text(self):
        text = "The weather is beautiful today. The sky is blue."
        claims = extract_claims(text)
        self.assertEqual(len(claims), 0)

    def test_mixed_claims(self):
        text = """The company reported strong earnings last quarter. 
                 The office has a new coffee machine. 
                 Tesla's stock price reached $900 on Friday. 
                 The quarterly profit margin was 15.3%."""
        claims = extract_claims(text)
        self.assertTrue(len(claims) >= 2)  # Should at least catch the stock price and profit margin claims
        # Check for specific claims, ignoring punctuation
        stock_claim = "Tesla's stock price reached $900 on Friday"
        margin_claim = "The quarterly profit margin was 15.3%"
        found_claims = [claim.rstrip('.') for claim in claims]
        self.assertTrue(any(stock_claim in claim for claim in found_claims))
        self.assertTrue(any(margin_claim in claim for claim in found_claims))

    def test_empty_input(self):
        text = ""
        claims = extract_claims(text)
        self.assertEqual(len(claims), 0)

if __name__ == '__main__':
    unittest.main() 