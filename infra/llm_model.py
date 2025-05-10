from langchain_google_genai import ChatGoogleGenerativeAI

class LLMModel:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(temperature=0.7, model="gemini-2.0-flash-001")