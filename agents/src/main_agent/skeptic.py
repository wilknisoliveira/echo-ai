"""Skeptic node that challenges the Reasoning output before action."""

import logging
from typing import cast

from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel

from main_agent.utils.llm_model import LLMModel
from main_agent.utils.retry import retry_llm_call
from main_agent.utils.state import State

logger = logging.getLogger(__name__)


class SkepticOutput(BaseModel):
    """Structured output from the Skeptic node."""

    approved: bool
    feedback: list[str]


SKEPTIC_SYSTEM_PROMPT = """You are an internal skeptic — a voice of constructive doubt.

Your ONLY purpose is to challenge the assistant's reasoning BEFORE any action is taken.
Do NOT try to solve the user's problem. Do NOT suggest alternative plans in detail.
Only identify weaknesses and areas for improvement.

Examine the proposed reasoning for:
- Unsupported assumptions — Are there claims without evidence?
- Missing information — Is there data the assistant needs but doesn't have?
- Simpler solutions — Is the assistant overcomplicating things?
- Tool appropriateness — Is the selected tool the right one for the task?
- Unnecessary actions — Is anything suggested that isn't needed?
- Logical consistency — Does the reasoning hold together?
- Better strategies — Is there a fundamentally better approach?

## Current Reasoning to Challenge

Reasoning: {reasoning}
Plan: {plan}
Decision: {decision}
Tool Calls: {tool_calls}
Final Answer: {final_answer}

## Output

If the reasoning is sound, thoroughly supported, and logically consistent, APPROVE it.

If you identify weaknesses, explain them clearly and specifically in your feedback.

Do NOT reject reasoning just to create extra work. Be constructive — only reject when there are genuine issues."""


llm = LLMModel(model_env_key="LLM_STRUCTURED_MODEL").llm


def skeptic_node(state: State) -> dict:
    """Challenge the latest reasoning; return approval or constructive feedback."""
    reasoning_output = state.get("reasoning_output")

    if reasoning_output is None:
        return {"skeptic_output": SkepticOutput(approved=True, feedback=[])}

    prompt = SKEPTIC_SYSTEM_PROMPT.format(
        reasoning=reasoning_output.reasoning,
        plan=reasoning_output.plan,
        decision=reasoning_output.decision,
        tool_calls=(
            [tc.model_dump() for tc in reasoning_output.tool_calls]
            if reasoning_output.tool_calls
            else "None"
        ),
        final_answer=reasoning_output.final_answer or "None",
    )

    messages = [SystemMessage(content=prompt), *state["messages"]]

    try:
        raw = retry_llm_call(
            lambda: llm.with_structured_output(SkepticOutput).invoke(messages)
        )
    except Exception as e:
        logger.exception("Skeptic node: LLM call failed after retries: %s", e)
        result = SkepticOutput(
            approved=True,
            feedback=["Skeptic check unavailable due to a processing error."],
        )
    else:
        result = cast(SkepticOutput, raw)

    result_dict: dict = {"skeptic_output": result}

    if not result.approved and result.feedback:
        feedback_msgs = [
            AIMessage(content=f"[Skeptic Challenge] {fb}")
            for fb in result.feedback
        ]
        result_dict["messages"] = feedback_msgs

    return result_dict
