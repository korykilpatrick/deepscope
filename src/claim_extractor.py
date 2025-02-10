import os
import spacy
from typing import List
from dotenv import load_dotenv

from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate

load_dotenv()
nlp = spacy.load("en_core_web_sm")

prompt_template = PromptTemplate(
    input_variables=["sentences"],
    template="""
You are given text sentences that may or may not contain falsifiable claims.
A "falsifiable claim" is a statement of fact that can be proven or disproven with evidence.
Review each sentence below and output ONLY those that qualify as check-worthy claims, 
separated by newlines. If none qualify, return an empty string.

Sentences:
{sentences}

Check-worthy claims:
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
    Splits the text into sentences, then uses an LLM to decide which are factual claims.
    """
    if not text.strip():
        return []

    # 1. Sentence split with spaCy
    doc = nlp(text)
    raw_sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    # 2. Feed all sentences to the LLM
    joined = "\n".join(raw_sentences)
    llm_output = chain.invoke({"sentences": joined})

    # 3. Parse results
    final_claims = [line.strip() for line in llm_output.split("\n") if line.strip()]
    return final_claims