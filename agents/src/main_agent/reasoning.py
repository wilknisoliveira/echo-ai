"""Reasoning node for the cognitive reasoning workflow."""

import logging
import os
from datetime import datetime
from typing import Any, Literal, cast

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from pydantic import BaseModel

from main_agent.utils.llm_model import LLMModel
from main_agent.utils.retry import retry_llm_call
from main_agent.utils.state import State
from main_agent.utils.tools.memory_tool import prepare_memories, upsert_memory

logger = logging.getLogger(__name__)

MAX_ITERATIONS = max(1, int(os.getenv("MAX_ITERATIONS", "5")))


class ToolCallRequest(BaseModel):
    """A single tool invocation requested by the Reasoning node."""

    name: str
    args: dict[str, Any]
    id: str | None = None


class ReasoningOutput(BaseModel):
    """Structured output from the Reasoning node."""

    reasoning: str
    plan: str
    decision: Literal["call_tools", "finish"]
    tool_calls: list[ToolCallRequest] = []
    final_answer: str | None = None


REASONING_SYSTEM_PROMPT = """You are a helpful personal assistant engaging in deliberate reasoning.

Your role is to assist the user by analyzing the situation, determining what information is needed, and deciding the best course of action.

## Your Thinking Process

1. **What do I know?** — Summarize the current state of information based on the conversation history.
2. **What's missing?** — Identify gaps in your knowledge that need to be filled.
3. **Do I need tools?** — Can you answer from what you know, or do you need external data?
4. **What's my plan?** — Decide on an approach.
5. **Can I answer now?** — If you have enough information, provide your final answer.

## Available Tools

{tool_descriptions}

## Context

{criticality}

{memories_current_time}

## Rules

- Only set decision to 'call_tools' if you genuinely need external information.
- When you have enough information, set decision to 'finish' and provide a complete answer.
- If you cannot complete the task, explain why in your final_answer.
- If you need clarification from the user, set decision to 'finish' and ask for it in final_answer.
- Your tool_calls must use valid tool names and correct arguments.
- Each tool_call must include a unique id string.
- Never set decision to 'call_tools' just to repeat reasoning you already have."""

FINAL_ITERATION_MESSAGE = "[SYSTEM] This is your final reasoning iteration. You must provide your best possible final answer and set decision to 'finish'. No further tool calls or iterations are allowed."


primary_assistant_tools = [TavilySearchResults(max_results=1), upsert_memory]

llm = LLMModel(model_env_key="LLM_STRUCTURED_MODEL").llm


def _build_reasoning_prompt(
    state: State,
    config: RunnableConfig,
    *,
    store: BaseStore,
    iteration_count: int,
) -> list[SystemMessage | Any]:
    criticality = state.get("context", {}).get("criticality", "")
    memories = prepare_memories(state, config, store=store)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tool_descriptions = "\n".join(
        f"- {tool.name}: {tool.description}" for tool in primary_assistant_tools
    )

    criticality_block = (
        f"\n## Criticality Analysis\n{criticality}\n" if criticality else ""
    )

    memories_block = f"{memories}" if memories else ""

    formatted_prompt = REASONING_SYSTEM_PROMPT.format(
        tool_descriptions=tool_descriptions,
        criticality=criticality_block,
        memories_current_time=memories_block + f"\nCurrent time: {current_time}.",
    )

    messages: list[Any] = [SystemMessage(content=formatted_prompt)]
    messages.extend(state["messages"])

    if iteration_count >= MAX_ITERATIONS:
        messages.append(SystemMessage(content=FINAL_ITERATION_MESSAGE))

    return messages


def _validate_reasoning_output(result: ReasoningOutput, iteration_count: int) -> None:
    """Validate ReasoningOutput for internal consistency. Raises on any violation."""
    if result.decision not in ("call_tools", "finish"):
        raise ValueError(
            f"Invalid Reasoning decision: {result.decision!r}. "
            f"Expected 'call_tools' or 'finish'."
        )

    if iteration_count >= MAX_ITERATIONS and result.decision != "finish":
        raise ValueError(
            f"Final iteration reached but Reasoning returned "
            f"decision={result.decision!r}. Must be 'finish'."
        )

    if result.decision == "call_tools" and not result.tool_calls:
        raise ValueError("Reasoning decision is 'call_tools' but tool_calls is empty.")

    if result.decision == "finish" and not result.final_answer:
        raise ValueError("Reasoning decision is 'finish' but final_answer is null.")


def reasoning_node(state: State, config: RunnableConfig, *, store: BaseStore) -> dict:
    """Execute the Reasoning node: analyze, plan, and decide next action."""
    iteration_count = state.get("iteration_count", 0) + 1

    prompt_messages = _build_reasoning_prompt(
        state, config, store=store, iteration_count=iteration_count
    )

    try:
        raw_result = retry_llm_call(
            lambda: llm.with_structured_output(ReasoningOutput, method="json_mode").invoke(prompt_messages)
        )
    except Exception as e:
        logger.error(
            "Reasoning node: LLM call failed after retries "
            "(iteration %d/%d): %s",
            iteration_count,
            MAX_ITERATIONS,
            e,
        )
        result = ReasoningOutput(
            reasoning="The model encountered an error while processing.",
            plan="N/A",
            decision="finish",
            final_answer=(
                "I'm sorry, I wasn't able to process that request. "
                "Please try rephrasing or ask me something else."
            ),
        )
    else:
        if raw_result is None:
            logger.error(
                "Reasoning node: LLM returned None for structured output "
                "(iteration %d/%d). Using fallback.",
                iteration_count,
                MAX_ITERATIONS,
            )
            result = ReasoningOutput(
                reasoning="The model encountered an error while processing.",
                plan="N/A",
                decision="finish",
                final_answer=(
                    "I'm sorry, I wasn't able to process that request. "
                    "Please try rephrasing or ask me something else."
                ),
            )
        else:
            result = cast(ReasoningOutput, raw_result)

    if iteration_count >= MAX_ITERATIONS and result.decision == "call_tools":
        result.decision = "finish"
        if not result.final_answer:
            result.final_answer = (
                "I've reached my analysis limit for this request. "
                "Here's what I've determined so far."
            )

    _validate_reasoning_output(result, iteration_count)

    messages: list[Any] = [
        AIMessage(
            content=f"**Reasoning:** {result.reasoning}\n\n**Plan:** {result.plan}"
        ),
    ]

    if result.decision == "finish" and result.final_answer:
        messages.append(AIMessage(content=result.final_answer))

    return {
        "messages": messages,
        "reasoning_output": result,
        "iteration_count": iteration_count,
    }
