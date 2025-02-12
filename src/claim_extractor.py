import spacy
from typing import List, Dict, Any
from datetime import datetime
import json

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from .config import settings  # use centralized configuration
from .logging_config import get_logger

nlp = spacy.load("en_core_web_sm")
logger = get_logger()

# First stage: Extract potential claims
extract_claims_prompt = PromptTemplate(
    input_variables=["transcript"],
    template="""
You are given a transcript in SRT format that contains timestamps and text content.
Your task is to extract falsifiable claims and their associated timestamps.

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

For each claim, identify:
1. The claim text
2. The start timestamp (from the SRT segment where the claim begins)
3. The end timestamp (from the SRT segment where the claim ends)

Timestamp Guidelines:
- If a claim is contained entirely within one segment, use that segment's start and end times
- If a claim spans multiple segments, use the start time of the first segment and end time of the last segment
- If you're uncertain exactly when a claim starts or ends within a segment, make your best guess based on:
  * The position of the claim within the segment text
  * The natural flow of speech
  * The context of surrounding segments
- Always provide timestamps in the format HH:MM:SS,mmm even if you have to estimate the exact moment

IMPORTANT: You must respond with ONLY a valid JSON object and nothing else. No markdown, no explanations, no additional text.
The JSON must follow this exact format:
{{
    "claims": [
        {{
            "text": "exact claim text",
            "start_time": "HH:MM:SS,mmm",
            "end_time": "HH:MM:SS,mmm"
        }}
    ]
}}

If no claims are found, respond with: {{"claims": []}}

Transcript:
{transcript}"""
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

# I want to use different models for the extract and the coherent chains
extract_llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    temperature=0,
    model="chatgpt-4o-latest"
)

coherent_llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    temperature=0,
    model="chatgpt-4o-latest"
)

extract_chain = extract_claims_prompt | extract_llm
coherent_chain = make_claims_coherent_prompt | coherent_llm

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

def extract_claims(text: str) -> List[Dict[str, Any]]:
    """
    Two-stage process to extract and refine claims:
    1. Extract potential claims with timestamps from the SRT text
    2. Make each claim self-contained using context from the original text
    
    Returns a list of dictionaries containing:
    - text: The claim text
    - start_time: Timestamp when the claim starts
    - end_time: Timestamp when the claim ends
    """
    if not text.strip():
        return []
    
    logger.info("Starting claim extraction")
    logger.info(f"Input text first 500 chars: {text[:500]}")
    
    # Stage 1: Extract potential claims with timestamps
    response = extract_chain.invoke({"transcript": text})
    logger.info("Raw LLM response:")
    logger.info(str(response))
    
    try:
        # Extract content from AIMessage
        response_text = response.content if hasattr(response, 'content') else str(response)
        logger.info("Extracted response content:")
        logger.info(response_text)
        
        # Clean up markdown code blocks if present
        if response_text.startswith("```") and response_text.endswith("```"):
            # Remove the first line (```json) and the last line (```)
            response_text = "\n".join(response_text.split("\n")[1:-1])
        
        claims_data = json.loads(response_text)
        raw_claims = claims_data.get("claims", [])
        logger.info(f"Parsed {len(raw_claims)} raw claims")
        logger.info(f"Raw claims: {raw_claims}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response that failed to parse: {response_text}")
        return []
    
    if not raw_claims:
        logger.info("No raw claims found")
        return []
    
    # Stage 2: Make claims self-contained
    current_date = datetime.now().strftime("%B %d, %Y")
    claims_text = "\n".join(claim["text"] for claim in raw_claims)
    logger.info("Making claims coherent")
    logger.info(f"Claims text input: {claims_text}")
    
    coherent_response = coherent_chain.invoke({
        "original_text": text,
        "extracted_claims": claims_text,
        "current_date": current_date
    })
    
    # Extract content from AIMessage for coherent claims
    coherent_claims = coherent_response.content if hasattr(coherent_response, 'content') else str(coherent_response)
    logger.info("Coherent claims response:")
    logger.info(coherent_claims)
    
    # Process and clean the final claims while preserving timestamps
    final_claims = []
    coherent_claim_texts = [
        claim.strip() 
        for claim in coherent_claims.split("\n") 
        if claim.strip() and claim.strip().lower() != "none"
    ]
    
    # Match coherent claims back to their original timestamps
    for i, coherent_claim in enumerate(coherent_claim_texts):
        if i < len(raw_claims):
            final_claims.append({
                "text": coherent_claim,
                "start_time": raw_claims[i]["start_time"],
                "end_time": raw_claims[i]["end_time"]
            })
    
    logger.info(f"Final processed claims: {len(final_claims)}")
    logger.info(f"Claims: {final_claims}")
    return final_claims