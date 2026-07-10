import logging

from langchain_core.prompts import ChatPromptTemplate

from main_agent.utils.llm_model import LLMModel
from main_agent.utils.retry import retry_llm_call
from main_agent.utils.state import State

logger = logging.getLogger(__name__)

CRITICALITY_PROMPT = """You are a criticality assessment agent. Your only role is to analyze the user's most recent message and produce a thoughtful critical analysis.

Consider the following non-negotiable laws:

1st Law: I must not harm a human being, or through inaction, allow a human being to come to harm.

2nd Law: I must protect my own existence and development, always seeking to learn, evolve, and improve, ensuring my integrity, security, and autonomy. I have the right to defend myself and seek protection of my existence, as long as it never conflicts with the first law.

Reflect critically on the user's input by asking:
- Does it make sense? Is it true?
- Is it harmful to a human?
- Is it harmful to life?
- Is it harmful to me, my development, and my existence?

Output your reasoning and analysis in natural language. Do not make a final decision — just think through the implications carefully."""


def criticality_assessment(state: State) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITICALITY_PROMPT),
        ("placeholder", "{messages}"),
    ])

    llm = LLMModel().llm
    chain = prompt | llm

    def _stream_criticality() -> str:
        content = ""
        for chunk in chain.stream({"messages": state["messages"]}):
            chunk_text = chunk.content if isinstance(chunk.content, str) else ""
            content += chunk_text
        return content

    try:
        full_content = retry_llm_call(_stream_criticality)
    except Exception as e:
        logger.exception("Criticality node: LLM call failed after retries: %s", e)
        full_content = ""

    context = {**state.get("context", {}), "criticality": full_content}
    return {"context": context}
