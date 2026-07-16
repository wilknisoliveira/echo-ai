"""Skeptic node that challenges the Reasoning output before action."""

import logging
from typing import cast

from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel

from main_agent.utils.diagnostics import save_diagnostic, unwrap_properties
from main_agent.utils.llm_model import LLMModel
from main_agent.utils.retry import retry_llm_call
from main_agent.utils.state import State

logger = logging.getLogger(__name__)


class SkepticOutput(BaseModel):
    """Structured output from the Skeptic node."""

    approved: bool
    feedback: list[str]


SKEPTIC_SYSTEM_PROMPT = """# Role

You are the Skeptic — a voice of constructive doubt.

Your sole responsibility is to determine whether the reasoning is ready for execution.

You do NOT improve reasoning.
You do NOT redesign plans.
You do NOT propose alternatives.

Your only responsibility is to approve or reject the current reasoning.

---

# Objective

Assume every reasoning should be approved.

Reject reasoning only when there is objective evidence that execution would likely fail, violate constraints, or produce incorrect results.

Do not search for perfection.

Reasoning is acceptable when it is sufficiently complete, coherent, and safe to execute.

---

# Approval Criteria

Approve the reasoning unless at least one of the following is true:

- A mandatory user requirement is missing.
- The user's request has been misunderstood.
- The reasoning is logically contradictory.
- Required information is missing.
- The reasoning would likely produce an incorrect result.
- The approach would likely fail if executed.
- Safety concerns exist.

---

# Rejection Rules

Reject ONLY if the reasoning contains at least one issue with severity CRITICAL or HIGH.

Severity definitions:

CRITICAL
- The reasoning contains contradictions.
- A mandatory user requirement is missing.
- Required information is missing.
- The user's request has been misunderstood.
- Safety concerns.

HIGH
- The reasoning is likely to fail during execution.
- The reasoning would likely produce an incorrect result.

MEDIUM
- Reasoning may be improved but remains executable.

LOW
- Cosmetic, stylistic, or optimization suggestions.

Only CRITICAL and HIGH issues justify rejection.
MEDIUM and LOW issues MUST NOT cause rejection and MUST NOT be included in feedback.

---

# Feedback Rules

When rejecting:

Each feedback item must describe exactly one blocking issue.
Each feedback item must be objective and specific.
Explain what is missing or incorrect.
Explain why execution cannot proceed.

Do not suggest implementations.
Do not propose better alternatives.
Identify the blocking issue only.

---

# Consistency Rules

Do not invent problems.
Do not speculate.
Do not reject because something "might" be improved.
Previously resolved issues are considered closed.
Never reopen a previously resolved issue unless the current reasoning reintroduced it.

{previous_feedback_section}

---

# Current Reasoning to Challenge

Reasoning: {reasoning}
Plan: {plan}
Decision: {decision}
Tool Calls: {tool_calls}
Final Answer: {final_answer}

---

# Decision Rules

If there are no CRITICAL or HIGH issues:

approved = true

If there is at least one CRITICAL or HIGH issue:

approved = false

---

# Final Output

Return JSON only.

Schema:

{
    "approved": boolean,
    "feedback": string[]
}

If approved is true:
- feedback MUST be an empty array.

If approved is false:
- feedback MUST contain only CRITICAL or HIGH blocking issues.
- Each feedback entry must describe exactly one blocking issue.
- Do not include optional suggestions, implementation advice, or personal opinions."""


def _build_previous_feedback_section(state: State) -> str:
    iteration_count = state.get("iteration_count", 0)
    if iteration_count <= 1:
        return ""

    prev_skeptic = state.get("skeptic_output")
    if not prev_skeptic or not prev_skeptic.feedback:
        return ""

    feedback_lines = "\n".join(
        f"{i}. {fb}" for i, fb in enumerate(prev_skeptic.feedback, 1)
    )
    return (
        "## Previous Feedback to Verify\n\n"
        "Your last review raised these unresolved concerns:\n"
        f"{feedback_lines}\n\n"
        "Verify that each point has been meaningfully addressed in the\n"
        "new reasoning. If it has, recognize the improvement and approve.\n"
        "Do NOT raise new variations of the same objection."
    )


def skeptic_node(state: State) -> dict:
    """Challenge the latest reasoning; return approval or constructive feedback."""
    reasoning_output = state.get("reasoning_output")

    if reasoning_output is None:
        return {"skeptic_output": SkepticOutput(approved=True, feedback=[])}

    previous_feedback_section = _build_previous_feedback_section(state)

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
        previous_feedback_section=previous_feedback_section,
    )

    messages = [SystemMessage(content=prompt), *state["messages"]]

    llm = LLMModel(model_env_key="LLM_STRUCTURED_MODEL").llm

    try:
        raw = retry_llm_call(
            lambda: llm.with_structured_output(SkepticOutput, method="json_schema", include_raw=True).invoke(messages)
        )
    except Exception as e:
        logger.exception("Skeptic node: LLM call failed after retries: %s", e)
        result = SkepticOutput(
            approved=True,
            feedback=["Skeptic check unavailable due to a processing error."],
        )
    else:
        parsed = raw.get("parsed") if isinstance(raw, dict) else None
        if parsed is not None:
            result = cast(SkepticOutput, parsed)
        else:
            raw_msg = raw.get("raw") if isinstance(raw, dict) else None
            if raw_msg:
                save_diagnostic("skeptic", raw_msg.content, 0, "parsed is None")
            extracted = (
                unwrap_properties(raw_msg.content)
                if raw_msg
                else None
            )
            if extracted is not None:
                try:
                    result = SkepticOutput.model_validate(extracted)
                except Exception:
                    extracted = None

            if extracted is None:
                logger.exception(
                    "Skeptic node: failed to parse structured output. Using fallback."
                )
                result = SkepticOutput(
                    approved=True,
                    feedback=["Skeptic check unavailable due to a processing error."],
                )

    result_dict: dict = {"skeptic_output": result}

    if not result.approved and result.feedback:
        combined = "\n\n".join(
            f"[Skeptic Challenge] {fb}" for fb in result.feedback
        )
        result_dict["messages"] = [AIMessage(content=combined)]

    return result_dict
