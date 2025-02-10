import unittest
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claim_extractor import extract_claims

class TestClaimExtractor(unittest.TestCase):
    def test_basic_factual_claim(self):
        text = "The Earth orbits around the Sun. This is a beautiful day."
        claims = extract_claims(text)
        self.assertEqual(len(claims), 1)
        expected = "The Earth orbits around the Sun"
        self.assertTrue(any(expected in claim.rstrip('.') for claim in claims))

    def test_non_factual_text(self):
        text = "I love sunny days! Isn't life wonderful?"
        claims = extract_claims(text)
        print(claims)
        self.assertEqual(len(claims), 0)  # Should find no falsifiable claims

    def test_mixed_claims(self):
        text = """Paris is the capital of France. 
                 I hope you're having a great day! 
                 Mount Everest is the tallest mountain on Earth. 
                 Water boils at 100 degrees Celsius at sea level."""
        claims = extract_claims(text)
        self.assertTrue(len(claims) >= 3)  # Should catch all three factual claims
        
        # Check for specific claims, ignoring punctuation
        expected_claims = [
            "Paris is the capital of France",
            "Mount Everest is the tallest mountain on Earth",
            "Water boils at 100 degrees Celsius at sea level"
        ]
        found_claims = [claim.rstrip('.') for claim in claims]
        for expected in expected_claims:
            self.assertTrue(
                any(expected in claim for claim in found_claims),
                f"Failed to find claim: {expected}"
            )

    def test_empty_input(self):
        text = ""
        claims = extract_claims(text)
        self.assertEqual(len(claims), 0)

    def test_single_sentence_multiple_claims(self):
        text = "The Moon orbits the Earth and Mars has two moons."
        claims = extract_claims(text)
        self.assertTrue(len(claims) >= 2)  # Should identify both claims

if __name__ == '__main__':
    unittest.main() 