import os

from langchain_openrouter import ChatOpenRouter


class LLMModel:
    def __init__(self, temperature: float=0.7, max_tokens: int | None=None, max_retries: int | None=None, model_env_key: str="LLM_MODEL"):
        llm_kwargs = {
            "model": os.getenv(model_env_key, "google/gemini-2.5-flash"),
            "temperature": temperature,
            **({"max_tokens": max_tokens} if max_tokens else {}),
        }
        retries = max_retries if max_retries is not None else int(os.getenv("LLM_MAX_RETRIES", "0"))
        if retries:
            llm_kwargs["max_retries"] = retries
        self.llm = ChatOpenRouter(**llm_kwargs)