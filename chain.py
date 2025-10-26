# app/chatbot/chain.py
import json
from typing import List, Dict, Any, Optional

from langchain.prompts import PromptTemplate

from .retriever import KBRetriever  # your sqlite text retriever (keeps fallback)
from .agent import create_llm
from .vector_store import KBVectorStore

# Initialize components
kb_sql_retriever = KBRetriever()  # fallback text retriever
kb_vector = KBVectorStore()
llm = create_llm()

# Prompt that forces context-only answers and JSON-safe structure
PROMPT_TEMPLATE = """
You are a clinical OCT assistant. Use ONLY the provided context documents. If the answer is not present in the context, reply exactly: "REQUIRES_DOCTOR_REVIEW".

Context documents:
{context}

Doctor question:
{question}

Provide a concise answer with these sections (if available): 
- disease (one-line)
- description (short)
- red_flags (bulleted)
- recommended_tests (bulleted)
- suggested_measures (bulleted)
- drugs (list with source)
- sources (list of source strings/urls)

Return the result as JSON ONLY. Do not invent facts. If unsure, set fields to null or empty lists and include "REQUIRES_DOCTOR_REVIEW" in the top-level note.
"""

prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])


def _build_context_from_vector_results(results: List[Dict[str, Any]]) -> str:
    """
    Assemble context text from top-K vector results.
    """
    ctx_parts = []
    for r in results:
        header = f"---\nDocument: {r.get('name')} (id={r.get('disease_id')})\nScore: {r.get('score')}\n"
        ctx_parts.append(header + r.get("detailed", ""))
    return "\n\n".join(ctx_parts)


def _llm_call(prompt_text: str) -> str:
    if not llm:
        raise RuntimeError("LLM not initialized")
    # CerebrasLLM wrapper implements __call__ as well as _call style; adapt to its interface
    # Some wrappers expect direct call; we try both
    try:
        return llm(prompt_text)
    except TypeError:
        # fallback if class uses ._call
        return llm._call(prompt_text)


def ask_doctor_question(disease_name: str, question: str) -> Dict[str, Any]:
    """
    Top-level function used by UI.
    Attempt vector retrieval first; fallback to sqlite text retriever.
    Returns: { response: dict_or_text, sources: [...], raw_llm: str }
    """
    # 1) Try vector search
    try:
        vr = kb_vector.search(disease_name, top_k=3)
    except Exception as e:
        vr = []

    if vr:
        context = _build_context_from_vector_results(vr)
        prompt_text = prompt.format(context=context, question=question)
        try:
            raw = _llm_call(prompt_text)
            # Try parse JSON from the model
            try:
                parsed = json.loads(raw)
                return {"response": parsed, "sources": [r.get("name") for r in vr], "raw_llm": raw}
            except Exception:
                # If parsing fails, return raw text but also include sources
                return {"response": {"text": raw, "note": "LLM output not JSON-parsable"}, "sources": [r.get("name") for r in vr], "raw_llm": raw}
        except Exception as e:
            # LLM failed — fallback to text retriever
            pass

    # 2) Fallback: SQLite text retrieval
    try:
        context_text = kb_sql_retriever.get_context(disease_name)
        return {"response": {"text": context_text}, "sources": [], "raw_llm": None}
    except Exception as e:
        return {"response": {"text": f"No KB available for '{disease_name}'. Please add entries."}, "sources": [], "raw_llm": None}
