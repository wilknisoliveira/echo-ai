import os

from langchain_openrouter import ChatOpenRouter


class LLMModel:
    def __init__(self, temperature: float=0.7, max_tokens: int | None=None, max_retries: int | None=None):
        llm_kwargs = {
            "model": os.getenv("LLM_MODEL", "google/gemini-2.5-flash"),
            "temperature": temperature,
            **({"max_tokens": max_tokens} if max_tokens else {}),
        }
        if max_retries is not None:
            llm_kwargs["max_retries"] = max_retries
        self.llm = ChatOpenRouter(**llm_kwargs)