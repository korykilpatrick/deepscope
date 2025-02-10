# claim_extractor.py

import re
import spacy
import os
from typing import List
from dotenv import load_dotenv
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Load environment variables from .env file
load_dotenv()

# Initialize spaCy
nlp = spacy.load("en_core_web_sm")

# A simple list of financial keywords to match in a sentence.
FINANCE_KEYWORDS = {
    "revenue", "profit", "earnings", "eps", "stock", "share", "dividend",
    "interest rate", "inflation", "ticker", "dow jones", "nasdaq", "sec filing",
    "guidance", "q1", "q2", "q3", "q4", "cash flow", "balance sheet", "edgar",
    "alpha vantage", "quarterly results", "margin", "financials"
}

# Custom prompt to ask an LLM to identify which sentences contain factual financial claims.
prompt_template = PromptTemplate(
    input_variables=["sentences"],
    template="""
You are given text sentences that may or may not contain factual financial claims. 
A "financial claim" is a statement about numeric or verifiable information related to finance, 
stock prices, company financials, or economic metrics. 
Review each sentence from the list below and output ONLY those that qualify as check-worthy 
financial claims, separated by newlines. If none qualify, return an empty string.

Sentences:
{sentences}

Check-worthy financial claims:
""",
)

# Initialize OpenAI with API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

llm = OpenAI(
    api_key=api_key,
    temperature=0,
    model="gpt-3.5-turbo-instruct"  # Using the instruct model for completions
)

# Create the chain using the newer pattern
chain = prompt_template | llm

def extract_claims(text: str) -> List[str]:
    """
    Splits the given text into sentences, performs a heuristic check
    for finance-related keywords, and then uses an LLM to confirm
    which sentences qualify as financial claims.
    """
    if not text.strip():
        return []

    # 1. Split text into sentences with spaCy
    doc = nlp(text)
    raw_sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    # 2. Heuristics: keep sentences that contain any finance keyword
    candidate_sentences = []
    for sentence in raw_sentences:
        lower_sentence = sentence.lower()
        if any(keyword in lower_sentence for keyword in FINANCE_KEYWORDS):
            candidate_sentences.append(sentence)

    if not candidate_sentences:
        return []

    # 3. Use LLM to finalize which sentences are actual financial claims
    joined_sentences = "\n".join(candidate_sentences)
    llm_output = chain.invoke({"sentences": joined_sentences})

    # 4. Parse the LLM's output to get the final claims (split by newlines)
    final_claims = [line.strip() for line in llm_output.split("\n") if line.strip()]
    return final_claims