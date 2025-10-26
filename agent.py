# app/chatbot/agent.py
from cerebras.cloud.sdk import Cerebras
from langchain.llms.base import LLM
from typing import Any, List


class CerebrasLLM(LLM):
    def __init__(self, api_key: str, model: str = "llama3.1-8b"):
        self.client = Cerebras(api_key=api_key)
        self.model = model

    @property
    def _llm_type(self) -> str:
        return "cerebras_llm"

    def _call(self, prompt: str, stop: List[str] | None = None) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )
        return response.choices[0].message["content"]


def create_llm():
    api_key = "csk-nd3vfeywmp43temxnvkvchxypv66jxm5xt93rj9pm6n2y63x"
    if not api_key:
        raise RuntimeError("CEREBRAS_API_KEY not set in env")
    try:
        return CerebrasLLM(api_key=api_key)
    except Exception as e:
        # surface the error so the developer knows why it failed
        raise RuntimeError(f"LLM initialization failed: {e}")

