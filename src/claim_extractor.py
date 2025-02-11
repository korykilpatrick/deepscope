import spacy
from typing import List
from datetime import datetime

from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate

from .config import settings  # use centralized configuration

nlp = spacy.load("en_core_web_sm")

# First stage: Extract potential claims
extract_claims_prompt = PromptTemplate(
    input_variables=["sentences"],
    template="""
You are given text sentences that may or may not contain falsifiable claims.
A "falsifiable claim" is a statement of fact that can be proven or disproven with evidence.

DO NOT include:
- Opinions or personal preferences (e.g., "I love pizza")
- Subjective statements (e.g., "The weather is beautiful")
- Questions or rhetorical additions (e.g., "isn't that wild?", "can you believe it?")
- Wishes or hopes
- Advice or recommendations (e.g., "You should buy this product")
- Emotional expressions
- Value judgments
- Commentary or reactions

ONLY include statements that:
- Can be verified with concrete evidence
- Have a clear true/false outcome
- Are objective and measurable

Extract all potential claims, even if they use pronouns or lack full context.
Split compound claims into separate statements.
Remove any subjective commentary or reactions.
Remove any leading or trailing punctuation.

Review each sentence below and output ONLY the factual claims,
separated by newlines. If none qualify, output an empty string.

Sentences:
{sentences}

Factual claims:
"""
)

# Second stage: Make claims self-contained
make_claims_coherent_prompt = PromptTemplate(
    input_variables=["original_text", "extracted_claims", "current_date"],
    template="""
You are given the original text and a list of extracted claims.
Your task is to make each claim COMPLETELY SELF-CONTAINED by using context from the original text.

Current date context: {current_date}

Rules for making claims self-contained:

1. ALWAYS resolve pronouns and references:
   ❌ "Their market share decreased" → ✅ "Microsoft's market share decreased"
   ❌ "The company announced" → ✅ "Google announced"
   ❌ "The system requires" → ✅ "Google's AI model requires"

2. Split compound claims into separate claims, repeating context for each:
   ❌ "Google's stock rose 10% while competitors fell 5%"
   ✅ "Google's stock price increased by 10% after their AI announcement"
   ✅ "Google's competitors' stock prices decreased by 5% after Google's AI announcement"

3. Handle temporal references using the current date:
   ❌ "Last year" → ✅ "In 2023" (if current date is 2024)
   ❌ "Last month" → ✅ "In February 2024" (if current date is March 2024)
   ❌ "Next quarter" → ✅ "In Q2 2024" (if current date is Q1 2024)

4. Resolve relative values and calculations:
   ❌ "double that number" → ✅ "increase from 20,000 to 40,000 units"
   ❌ "reduce this price by 10%" → ✅ "reduce the price from $47,490 to $42,741"

5. Maintain complete context in each claim:
   ❌ "The operating system only runs on 25% of PCs" 
   ✅ "Windows 11 runs on 25% of all personal computers"

6. Split claims with multiple measurements or facts:
   ❌ "The system requires 4 GPUs and costs $40,000"
   ✅ "Google's AI model requires 4 GPUs to run"
   ✅ "The 4 GPUs required for Google's AI model cost $40,000"

Original text:
{original_text}

Extracted claims:
{extracted_claims}

Output each claim in a fully self-contained form, one per line.
Each claim must be independently verifiable without any pronouns or relative references.
"""
)

llm = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    temperature=0,
    model="gpt-3.5-turbo-instruct"
)

extract_chain = extract_claims_prompt | llm
coherent_chain = make_claims_coherent_prompt | llm

def split_compound_claim(claim: str) -> List[str]:
    """
    Further splits a claim if it contains multiple independent verifiable statements.
    Uses spaCy to analyze the sentence structure and identify coordinate clauses.
    """
    doc = nlp(claim)
    
    # If the claim has no coordinating conjunction, return it as is
    if not any(token.dep_ == "cc" for token in doc):
        return [claim]
    
    independent_claims = []
    current_claim = []
    
    for token in doc:
        if token.dep_ == "cc" and current_claim:
            claim_text = " ".join(t.text for t in current_claim).strip()
            if claim_text:
                independent_claims.append(claim_text)
            current_claim = []
        else:
            current_claim.append(token)
    
    if current_claim:
        claim_text = " ".join(t.text for t in current_claim).strip()
        if claim_text:
            independent_claims.append(claim_text)
    
    # If splitting produced no useful results, return the original claim
    if not independent_claims or len(independent_claims) == 1:
        return [claim]
    
    return independent_claims

def extract_claims(text: str) -> List[str]:
    """
    Two-stage process to extract and refine claims:
    1. Extract potential claims from the text
    2. Make each claim self-contained using context from the original text
    """
    if not text.strip():
        return []
    
    # Stage 1: Extract potential claims
    initial_claims = extract_chain.invoke({"sentences": text})
    raw_claims = [
        claim.strip() 
        for claim in initial_claims.split("\n") 
        if claim.strip() and claim.strip().lower() != "none"
    ]
    
    # Split any compound claims
    split_claims = []
    for claim in raw_claims:
        split_claims.extend(split_compound_claim(claim))
    
    if not split_claims:
        return []
    
    # Stage 2: Make claims self-contained
    current_date = datetime.now().strftime("%B %d, %Y")
    claims_text = "\n".join(split_claims)
    coherent_claims = coherent_chain.invoke({
        "original_text": text,
        "extracted_claims": claims_text,
        "current_date": current_date
    })
    
    # Process and clean the final claims
    final_claims = [
        claim.strip() 
        for claim in coherent_claims.split("\n") 
        if claim.strip() and claim.strip().lower() != "none"
    ]
    
    return final_claims