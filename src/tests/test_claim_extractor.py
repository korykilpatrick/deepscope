import unittest
import sys
import os
from typing import List

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claim_extractor import extract_claims

class TestClaimExtractor(unittest.TestCase):
    def assertClaimsMatch(self, text: str, expected_claims: List[str], exact_count: bool = False):
        """
        Helper method to check if extracted claims match expected claims.
        Prints detailed comparison on failure.
        
        Args:
            text: Input text to extract claims from
            expected_claims: List of expected claims
            exact_count: If True, requires exact number of claims to match
        """
        claims = extract_claims(text)
        found_claims = [claim.rstrip('.').lower() for claim in claims]
        expected_lower = [claim.lower() for claim in expected_claims]
        
        # For exact count matching
        if exact_count and len(claims) != len(expected_claims):
            self.fail(
                f"\nClaim count mismatch!"
                f"\nExpected {len(expected_claims)} claims but got {len(claims)}"
                f"\n\nExpected claims:"
                f"\n" + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(expected_claims)) +
                f"\n\nActual claims:"
                f"\n" + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(claims))
            )
        
        # Check each expected claim is found
        missing_claims = []
        for expected in expected_claims:
            if not any(expected.lower() in claim for claim in found_claims):
                missing_claims.append(expected)
        
        # Check for unexpected extra claims
        extra_claims = []
        for found in claims:
            if not any(expected.lower() in found.lower() for expected in expected_claims):
                extra_claims.append(found)
        
        if missing_claims or extra_claims:
            failure_msg = "\nClaim extraction failed!"
            if missing_claims:
                failure_msg += "\n\nMissing expected claims:" 
                failure_msg += "\n" + "\n".join(f"  - {c}" for c in missing_claims)
            if extra_claims:
                failure_msg += "\n\nUnexpected extra claims:"
                failure_msg += "\n" + "\n".join(f"  + {c}" for c in extra_claims)
            failure_msg += "\n\nAll expected claims:"
            failure_msg += "\n" + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(expected_claims))
            failure_msg += "\n\nAll actual claims:"
            failure_msg += "\n" + "\n".join(f"  {i+1}. {c}" for i, c in enumerate(claims))
            self.fail(failure_msg)

    def test_basic_factual_claim(self):
        text = "The Earth orbits around the Sun. This is a beautiful day."
        expected_claims = ["The Earth orbits around the Sun"]
        self.assertClaimsMatch(text, expected_claims, exact_count=True)

    def test_non_factual_text(self):
        text = "I love sunny days! Isn't life wonderful?"
        claims = extract_claims(text)
        self.assertEqual(len(claims), 0, f"Expected no claims but got: {claims}")

    def test_mixed_claims(self):
        text = """Paris is the capital of France. 
                 I hope you're having a great day! 
                 Mount Everest is the tallest mountain on Earth. 
                 Water boils at 100 degrees Celsius at sea level."""
        expected_claims = [
            "Paris is the capital of France",
            "Mount Everest is the tallest mountain on Earth",
            "Water boils at 100 degrees Celsius at sea level"
        ]
        self.assertClaimsMatch(text, expected_claims, exact_count=True)

    def test_empty_input(self):
        text = ""
        claims = extract_claims(text)
        self.assertEqual(len(claims), 0)

    def test_single_sentence_multiple_claims(self):
        text = "The Moon orbits the Earth and Mars has two moons."
        expected_claims = [
            "The Moon orbits the Earth",
            "Mars has two moons"
        ]
        self.assertClaimsMatch(text, expected_claims, exact_count=True)

    def test_health_wellness_transcript(self):
        text = """
        Good morning beautiful people! Today I want to talk about some amazing health facts that changed my life! 
        Scientists at Stanford University discovered last month that drinking lemon water increases metabolism by 30%. 
        I've been doing this for just 2 weeks and feel amazing!

        Let me drop some truth bombs: The average American consumes 152 pounds of sugar annually, and artificial sweeteners 
        are found in 75% of processed foods. The human body can distinguish between over 1 trillion different scents - isn't that wild? 
        My favorite supplement, Vitamin D3, was shown in a 2023 study to reduce seasonal depression by 60%.

        During the pandemic, meditation app downloads increased by 2000%. I think everyone should meditate, it's literally life-changing! 
        Also, research shows that people who exercise in the morning burn 200% more fat, and green tea contains 254 known beneficial compounds. 
        Trust me, I've done my research! Don't forget to like and subscribe! #WellnessWarrior #HealthFacts
        """
        expected_claims = [
            "Scientists at Stanford University discovered last month that drinking lemon water increases metabolism by 30%",
            "The average American consumes 152 pounds of sugar annually",
            "artificial sweeteners are found in 75% of processed foods",
            "The human body can distinguish between over 1 trillion different scents",
            "Vitamin D3 was shown in a 2023 study to reduce seasonal depression by 60%",
            "During the pandemic, meditation app downloads increased by 2000%",
            "people who exercise in the morning burn 200% more fat",
            "green tea contains 254 known beneficial compounds"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_tech_review_transcript(self):
        text = """
        What's up tech fam! Breaking news about the latest iPhone 15 Pro that nobody's talking about. 
        According to the official specs, the new A17 chip processes AI tasks 40% faster than the A16. 
        The phone's been out for 3 months and has already sold 50 million units worldwide, making it the fastest-selling iPhone ever.

        Fun fact: The first iPhone only had 128MB of RAM, while this new one has 8GB. That's a 6250% increase! 
        The battery can supposedly last 29 hours of video playback, but in my tests, I only got 22 hours. 
        Samsung's market share dropped to 19% this quarter, their lowest since 2009.

        The new titanium frame is allegedly 45% lighter than steel, and they claim it's "the most durable smartphone ever made." 
        The factory in India produces 250,000 units daily, and they're using 100% renewable energy in production.
        """
        expected_claims = [
            "the new A17 chip processes AI tasks 40% faster than the A16",
            "The phone's been out for 3 months",
            "sold 50 million units worldwide",
            "The first iPhone only had 128MB of RAM",
            "this new one has 8GB",
            "Samsung's market share dropped to 19% this quarter",
            "The new titanium frame is 45% lighter than steel",
            "The factory in India produces 250,000 units daily",
            "they're using 100% renewable energy in production"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_political_transcript(self):
        text = """
        Hey everyone! Just watched the State budget announcement and I need to break this down. 
        The government claims they're increasing education spending by 45% this year, but let me give you the real story. 
        Back in 2019, California actually spent more per student than any other state, at $14,827 per student. 
        Here's the thing - Australia's current GDP is 1.7 trillion dollars, and we're only spending 2% of that on education. 
        The last time unemployment was this low - 3.5% - was in 1974!

        I personally think these policies are terrible, but what's really concerning is that the average classroom size 
        has increased to 32 students this year. The Minister of Education graduated from Harvard in 1995, but she's never 
        actually taught in a public school. By the way, did you know that 78% of teachers are buying their own supplies?
        """
        expected_claims = [
            "increasing education spending by 45% this year",
            "California spent more per student than any other state",
            "spent $14,827 per student",
            "Australia's current GDP is 1.7 trillion dollars",
            "spending 2% of that on education",
            "unemployment was 3.5%",
            "was in 1974",
            "average classroom size has increased to 32 students this year",
            "Minister of Education graduated from Harvard in 1995",
            "78% of teachers are buying their own supplies"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_complex_compound_claims(self):
        text = """
        The new study shows that coffee reduces cancer risk by 15% and improves memory function by 20%, while also 
        increasing alertness for up to 6 hours. Research indicates that regular exercise extends lifespan by 5 years, 
        reduces heart disease risk by 30%, and improves mental health outcomes by 45%. The company's revenue grew by 
        25% last quarter but their market share decreased by 10%.
        """
        expected_claims = [
            "coffee reduces cancer risk by 15%",
            "improves memory function by 20%",
            "increasing alertness for up to 6 hours",
            "regular exercise extends lifespan by 5 years",
            "reduces heart disease risk by 30%",
            "improves mental health outcomes by 45%",
            "company's revenue grew by 25% last quarter",
            "their market share decreased by 10%"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_claims_with_temporal_markers(self):
        text = """
        Last year, global temperatures reached a record high of 1.5°C above pre-industrial levels. 
        By 2025, electric vehicles will account for 30% of all new car sales. 
        Since 2010, renewable energy costs have dropped by 85%, and solar installation has increased by 2000%.
        """
        expected_claims = [
            "global temperatures reached a record high of 1.5°C above pre-industrial levels",
            "electric vehicles will account for 30% of all new car sales",
            "renewable energy costs have dropped by 85%",
            "solar installation has increased by 2000%"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_pronoun_resolution(self):
        text = """
        Apple released the iPhone 15 Pro last month. It features a new A17 chip and costs $999. 
        The company says they've sold millions already. Their market share has increased by 20% since the launch.
        The device is made of titanium, which they claim makes it more durable.
        """
        expected_claims = [
            "Apple released the iPhone 15 Pro last month",
            "The iPhone 15 Pro features the A17 chip",
            "The iPhone 15 Pro costs $999",
            "Apple has sold millions of iPhone 15 Pro units",
            "Apple's market share has increased by 20% since the iPhone 15 Pro launch",
            "The iPhone 15 Pro is made of titanium"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_relative_reference_expansion(self):
        text = """
        Tesla's Model Y costs $47,490. They're planning to reduce this price by 10% next month.
        The car can go 330 miles on a single charge. This range increases to 400 miles with the long-range battery.
        The company made 20,000 units last month, and they plan to double that number by December.
        """
        expected_claims = [
            "Tesla's Model Y costs $47,490",
            "Tesla plans to reduce the Model Y price to $42,741 next month",
            "The Tesla Model Y can travel 330 miles on a single charge",
            "The Tesla Model Y with long-range battery can travel 400 miles on a single charge",
            "Tesla produced 20,000 Model Y units last month",
            "Tesla plans to produce 40,000 Model Y units in December"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_compound_claims_with_context(self):
        text = """
        Microsoft's revenue hit $100 billion in 2023, and their cloud division grew by 50%.
        The company hired 5,000 engineers and opened three new data centers in Asia.
        Windows 11 has 500 million users, but the OS only runs on 25% of all PCs.
        """
        expected_claims = [
            "Microsoft's revenue hit $100 billion in 2023",
            "Microsoft's cloud division grew by 50% in 2023",
            "Microsoft hired 5,000 engineers",
            "Microsoft opened three new data centers in Asia",
            "Windows 11 has 500 million users",
            "Windows 11 runs on 25% of all PCs"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_subjective_qualifier_removal(self):
        text = """
        Experts claim the new drug reduces cancer risk by 40%. 
        The company allegedly saved $50 million through automation.
        Scientists believe they've discovered a new planet, which they say is 20% larger than Earth.
        The CEO supposedly earned $10 million in stock options last year.
        """
        expected_claims = [
            "The drug reduces cancer risk by 40%",
            "The company saved $50 million through automation",
            "The discovered planet is 20% larger than Earth",
            "The CEO earned $10 million in stock options last year"
        ]
        self.assertClaimsMatch(text, expected_claims)

    def test_mixed_context_preservation(self):
        text = """
        In a major announcement today, Google unveiled their new AI model. It processes tasks 5x faster 
        than their previous version and uses 30% less energy. The company spent $2 billion on its development,
        and they claim it's already being used by 100 enterprise customers. Their stock jumped 10% after 
        this news, while their main competitor saw a 5% drop. The system requires 4 GPUs to run, which 
        costs about $40,000.
        """
        expected_claims = [
            "Google's new AI model processes tasks 5 times faster than Google's previous AI model",
            "Google's new AI model uses 30% less energy than their previous AI model",
            "Google spent $2 billion on developing their new AI model",
            "Google's new AI model is being used by 100 enterprise customers",
            "Google's stock price increased by 10% after the AI model announcement",
            "Google's main competitor's stock price decreased by 5% after Google's AI announcement",
            "Google's new AI model requires 4 GPUs to run",
            "The 4 GPUs required for Google's new AI model cost $40,000"
        ]
        self.assertClaimsMatch(text, expected_claims)

if __name__ == '__main__':
    unittest.main() 