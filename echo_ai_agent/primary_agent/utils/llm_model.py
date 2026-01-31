from langchain_google_genai import ChatGoogleGenerativeAI

class LLMModel:
    def __init__(self, temperature: float=0.7, max_tokens: int | None=None):
        llm_kwargs = {
            "model": "gemini-2.5-flash",
            "temperature": temperature,
            **({"max_tokens": max_tokens} if max_tokens else {})
        }
        self.llm = ChatGoogleGenerativeAI(**llm_kwargs)