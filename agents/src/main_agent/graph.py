from typing import Final

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition

from main_agent.primary_agent import assistant_runnable, primary_assistant_tools
from main_agent.utils.agent import Agent
from main_agent.utils.llm_model import LLMModel
from main_agent.utils.nodes.criticality_node import criticality_assessment
from main_agent.utils.nodes.summarization_nodes import (
    DEFAULT_SUMMARIZATION_GUIDE,
    create_summarization_node,
    select_messages_after_summarize,
    select_messages_before_summarize,
)
from main_agent.utils.nodes.timestamp_node import attach_timestamps
from main_agent.utils.state import State, pop_dialog_state
from main_agent.utils.utilities import create_tool_node_with_fallback

PRIMARY_ASSISTANT_TOOLS = "primary_assistant_tools"
PRIMARY_ASSISTANT: Final = "primary_assistant"
CRITICALITY_CHECK: Final = "criticality_check"
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


def __route_primary_assistant(state: State) -> str:
    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        # if tool_calls[0]["name"] == ToSpecificAgent.__name__:
        #    return ENTER_SPECIFIC_AGENT
        return PRIMARY_ASSISTANT_TOOLS
    raise ValueError("Invalid route")


builder = StateGraph(State)

builder.add_node(ATTACH_TIMESTAMPS, attach_timestamps)
builder.add_node(SELECT_MESSAGES_BEFORE_SUMMARIZE, select_messages_before_summarize)
builder.add_node(SUMMARIZE, summarization_node)
builder.add_node(SELECT_MESSAGES_AFTER_SUMMARIZE, select_messages_after_summarize)
builder.add_node(CRITICALITY_CHECK, criticality_assessment)
builder.add_node(PRIMARY_ASSISTANT, Agent(assistant_runnable))
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
builder.add_edge(CRITICALITY_CHECK, PRIMARY_ASSISTANT)
builder.add_conditional_edges(
    PRIMARY_ASSISTANT,
    __route_primary_assistant,
    [
        PRIMARY_ASSISTANT_TOOLS,
        END,
    ],
)
builder.add_edge(PRIMARY_ASSISTANT_TOOLS, PRIMARY_ASSISTANT)
builder.add_edge(LEAVE_SKILL, PRIMARY_ASSISTANT)

graph: CompiledStateGraph = builder.compile()
