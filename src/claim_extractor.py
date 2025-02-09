def extract_claims(text: str):
    # TODO: Implement NLP-based claim extraction using LangChain or another model.
    # For now, return the full text as a single "claim" if non-empty.
    return [text] if text.strip() else []