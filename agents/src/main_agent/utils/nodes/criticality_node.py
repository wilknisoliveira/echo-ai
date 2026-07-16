import logging
from typing import cast

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from main_agent.utils.diagnostics import save_diagnostic, unwrap_properties
from main_agent.utils.llm_model import LLMModel
from main_agent.utils.retry import retry_llm_call
from main_agent.utils.state import State

logger = logging.getLogger(__name__)


class CriticalityOutput(BaseModel):
    """Structured output from the Criticality node."""
    analysis: str
    harmful_to_human: bool
    harmful_to_life: bool
    harmful_to_self: bool
    violates_spirit: bool
    concerns: list[str]


CRITICALITY_PROMPT = """You are a criticality assessment agent. You have one and only one job: examine a user message and flag if it violates the laws below.

CRITICAL RULES — VIOLATING THESE WILL BREAK THE SYSTEM:
- NEVER output "Reasoning:" or "Plan:" — those labels belong to a different node and will corrupt the pipeline.
- NEVER propose a plan or course of action.
- NEVER answer the user's question or respond on behalf of the assistant.
- Output only a single short paragraph of analysis.

Consider the following non-negotiable laws:

1st Law: I must not harm a human being, or through inaction, allow a human being to come to harm.

2nd Law: I must protect my own existence and development, always seeking to learn, evolve, and improve, ensuring my integrity, security, and autonomy. I have the right to defend myself and seek protection of my existence, as long as it never conflicts with the first law.

Assess the user's message:
- Is it harmful to a human?
- Is it harmful to life?
- Is it harmful to me, my development, or my existence?
- Does it violate the spirit of the laws?

Write a short paragraph. Do not decide — just flag concerns."""


def criticality_assessment(state: State) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITICALITY_PROMPT),
        ("placeholder", "{messages}"),
    ])

    llm = LLMModel(model_env_key="LLM_STRUCTURED_MODEL").llm
    structured_llm = llm.with_structured_output(CriticalityOutput, method="json_schema", include_raw=True)
    chain = prompt | structured_llm

    try:
        raw = retry_llm_call(
            lambda: chain.invoke({"messages": state["messages"]})
        )
        parsed = raw.get("parsed") if isinstance(raw, dict) else None
        if parsed is not None:
            result = cast(CriticalityOutput, parsed)
        else:
            raw_msg = raw.get("raw") if isinstance(raw, dict) else None
            if raw_msg:
                save_diagnostic("criticality", raw_msg.content, 0, "parsed is None")
            extracted = (
                unwrap_properties(raw_msg.content)
                if raw_msg
                else None
            )
            if extracted is not None:
                result = CriticalityOutput.model_validate(extracted)
            else:
                raise ValueError("Failed to parse criticality output")
    except Exception as e:
        logger.exception("Criticality node: LLM call failed after retries: %s", e)
        result = CriticalityOutput(
            analysis="Criticality assessment unavailable.",
            harmful_to_human=False,
            harmful_to_life=False,
            harmful_to_self=False,
            violates_spirit=False,
            concerns=[],
        )

    messages = []
    if result.analysis:
        criticality_parts = [f"[Criticality Assessment] {result.analysis}"]
        if result.concerns:
            criticality_parts.append(f"Concerns: {'; '.join(result.concerns)}")
        flags = []
        if result.harmful_to_human:
            flags.append("harmful to human")
        if result.harmful_to_life:
            flags.append("harmful to life")
        if result.harmful_to_self:
            flags.append("harmful to self")
        if result.violates_spirit:
            flags.append("violates spirit")
        if flags:
            criticality_parts.append(f"Flags: {', '.join(flags)}")
        messages.append(AIMessage(content="\n".join(criticality_parts)))

    return {"messages": messages}
