import os
import re
import spacy
from typing import List
from dotenv import load_dotenv

from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

load_dotenv()
nlp = spacy.load("en_core_web_sm")

# Basic financial keyword set to reduce unnecessary LLM calls.
FINANCE_KEYWORDS = {
    "revenue", "profit", "earnings", "eps", "stock", "share", "dividend",
    "interest rate", "inflation", "ticker", "dow jones", "nasdaq", "sec filing",
    "guidance", "q1", "q2", "q3", "q4", "cash flow", "balance sheet", "edgar",
    "alpha vantage", "quarterly results", "margin", "financials"
}

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
"""
)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set")

llm = OpenAI(
    api_key=api_key,
    temperature=0,
    model="gpt-3.5-turbo-instruct"
)
chain = prompt_template | llm

def extract_claims(text: str) -> List[str]:
    """
    Splits the text into sentences, filters by finance keywords,
    and then uses an LLM to finalize which are actual financial claims.
    """
    if not text.strip():
        return []

    # 1. Sentence split with spaCy
    doc = nlp(text)
    raw_sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    # 2. Quick heuristics
    candidate_sentences = []
    for sentence in raw_sentences:
        if any(k in sentence.lower() for k in FINANCE_KEYWORDS):
            candidate_sentences.append(sentence)

    if not candidate_sentences:
        return []

    # 3. LLM for final filtering
    joined = "\n".join(candidate_sentences)
    llm_output = chain.invoke({"sentences": joined})
    final_claims = [line.strip() for line in llm_output.split("\n") if line.strip()]
    return final_claims