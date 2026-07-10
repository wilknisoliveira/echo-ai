"""LangGraph definition for the cognitive reasoning workflow."""

import uuid
from typing import Any, Final

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from main_agent.reasoning import MAX_ITERATIONS, primary_assistant_tools, reasoning_node
from main_agent.skeptic import skeptic_node
from main_agent.utils.llm_model import LLMModel
from main_agent.utils.nodes.criticality_node import criticality_assessment
from main_agent.utils.nodes.summarization_nodes import (
    DEFAULT_SUMMARIZATION_GUIDE,
    create_summarization_node,
    select_messages_after_summarize,
    select_messages_before_summarize,
)
from main_agent.utils.nodes.timestamp_node import attach_timestamps
from main_agent.utils.retry import retry_llm_call
from main_agent.utils.state import State, pop_dialog_state
from main_agent.utils.utilities import create_tool_node_with_fallback

PRIMARY_ASSISTANT_TOOLS = "primary_assistant_tools"
REASONING: Final = "reasoning"
CRITICALITY_CHECK: Final = "criticality_check"
SKEPTIC: Final = "skeptic"
PREPARE_TOOL_CALLS: Final = "prepare_tool_calls"
SELECT_MESSAGES_BEFORE_SUMMARIZE = "select_messages_before_summarize"
SELECT_MESSAGES_AFTER_SUMMARIZE = "select_messages_after_summarize"
ATTACH_TIMESTAMPS = "attach_timestamps"
SUMMARIZE = "summarize"
LEAVE_SKILL = "leave_skill"

summarization_node = create_summarization_node(
    model=LLMModel(max_tokens=3000).llm,
    max_tokens=10000,
    max_summary_tokens=3000,
    max_tokens_before_summary=9500,
    summary_guide=DEFAULT_SUMMARIZATION_GUIDE,
)


def __route_after_reasoning(state: State) -> str:
    count = state.get("iteration_count", 0)
    if count >= MAX_ITERATIONS:
        return END
    return SKEPTIC


def _route_after_review(state: State) -> str:
    skeptic = state["skeptic_output"]

    if not skeptic.approved:
        return REASONING

    reasoning = state["reasoning_output"]

    if reasoning.decision == "call_tools":
        return PREPARE_TOOL_CALLS

    if reasoning.decision == "finish":
        return END

    raise ValueError(
        f"Unknown reasoning decision: {reasoning.decision!r}"
    )


def _prepare_tool_calls_inner(state: State) -> dict:
    reasoning_output = state.get("reasoning_output")
    if reasoning_output is None or not reasoning_output.tool_calls:
        return {"messages": []}

    tool_calls: list[dict[str, Any]] = []
    for tc in reasoning_output.tool_calls:
        tool_calls.append({
            "name": tc.name,
            "args": tc.args,
            "id": tc.id or str(uuid.uuid4()),
        })

    return {"messages": [AIMessage(content="", tool_calls=tool_calls)]}


builder = StateGraph(State)

builder.add_node(ATTACH_TIMESTAMPS, attach_timestamps)
builder.add_node(SELECT_MESSAGES_BEFORE_SUMMARIZE, select_messages_before_summarize)
builder.add_node(SUMMARIZE, lambda state: retry_llm_call(lambda: summarization_node.invoke(state)))
builder.add_node(SELECT_MESSAGES_AFTER_SUMMARIZE, select_messages_after_summarize)
builder.add_node(CRITICALITY_CHECK, criticality_assessment)
builder.add_node(REASONING, reasoning_node)
builder.add_node(SKEPTIC, skeptic_node)
builder.add_node(
    PREPARE_TOOL_CALLS,
    lambda state: _prepare_tool_calls_inner(state),
)
builder.add_node(
    PRIMARY_ASSISTANT_TOOLS,
    create_tool_node_with_fallback(primary_assistant_tools),
)
builder.add_node(LEAVE_SKILL, pop_dialog_state)

builder.add_edge(START, ATTACH_TIMESTAMPS)
builder.add_edge(ATTACH_TIMESTAMPS, SELECT_MESSAGES_BEFORE_SUMMARIZE)
builder.add_edge(SELECT_MESSAGES_BEFORE_SUMMARIZE, SUMMARIZE)
builder.add_edge(SUMMARIZE, SELECT_MESSAGES_AFTER_SUMMARIZE)
builder.add_edge(SELECT_MESSAGES_AFTER_SUMMARIZE, CRITICALITY_CHECK)
builder.add_edge(CRITICALITY_CHECK, REASONING)

builder.add_conditional_edges(
    REASONING,
    __route_after_reasoning,
    {
        SKEPTIC: SKEPTIC,
        END: END,
    },
)

builder.add_conditional_edges(
    SKEPTIC,
    _route_after_review,
    {
        REASONING: REASONING,
        PREPARE_TOOL_CALLS: PREPARE_TOOL_CALLS,
        END: END,
    },
)

builder.add_edge(PREPARE_TOOL_CALLS, PRIMARY_ASSISTANT_TOOLS)

builder.add_edge(PRIMARY_ASSISTANT_TOOLS, REASONING)

builder.add_edge(LEAVE_SKILL, REASONING)

graph: CompiledStateGraph = builder.compile()
