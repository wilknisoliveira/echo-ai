import os
from typing import Literal, Final

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from sqlalchemy.ext.asyncio import create_async_engine

from psycopg_pool import ConnectionPool

from echo_ai_agent.primary_agent import assistant_runnable, primary_assistant_tools
from echo_ai_agent.utils.agent import Agent
from echo_ai_agent.utils.state import State, pop_dialog_state, LEAVE_SKILL
from echo_ai_agent.utils.utilities import create_tool_node_with_fallback

PRIMARY_ASSISTANT_TOOLS = "primary_assistant_tools"
PRIMARY_ASSISTANT: Final = "primary_assistant"
DB_URI = os.environ["DB_URI"]

def route_primary_assistant(state: State):
    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        #if tool_calls[0]["name"] == ToSpecificAgent.__name__:
        #    return ENTER_SPECIFIC_AGENT
        return PRIMARY_ASSISTANT_TOOLS
    raise ValueError("Invalid route")

# Each specialized agent can directly respond to the user
# When user responds, return to the currently active workflow
# Add here the Agents routes
def route_to_workflow(
    state: State,
) -> Literal[
    PRIMARY_ASSISTANT
]:
    """If we are in a delegated state, route directly to the appropriate assistant."""
    dialog_state = state.get("dialog_state")
    if not dialog_state:
        return PRIMARY_ASSISTANT
    return dialog_state[-1]

builder = StateGraph(State)
# Get the user info at begging
builder.add_edge(START, PRIMARY_ASSISTANT)

# Add here the Subgraph

builder.add_node(LEAVE_SKILL, pop_dialog_state)
builder.add_edge(LEAVE_SKILL, PRIMARY_ASSISTANT)

builder.add_node(PRIMARY_ASSISTANT, Agent(assistant_runnable))
builder.add_node(PRIMARY_ASSISTANT_TOOLS, create_tool_node_with_fallback(primary_assistant_tools))

# Use the custom instead of tools_condition
builder.add_conditional_edges(
    PRIMARY_ASSISTANT,
    route_primary_assistant,
    [
        PRIMARY_ASSISTANT_TOOLS,
        END,
    ],
)
builder.add_edge(PRIMARY_ASSISTANT_TOOLS, PRIMARY_ASSISTANT)

pool = ConnectionPool(
    conninfo=DB_URI,
    min_size=5,
    max_size=20,
    timeout=30
)

with pool.connection() as conn:
    conn.autocommit = True
    short_term_memory = PostgresSaver(conn)
    short_term_memory.setup()

short_term_memory = PostgresSaver(pool)

graph = builder.compile(
    checkpointer=short_term_memory
)

print("Graph Mermaid Code")
print("--------START---------")
try:
    print(graph.get_graph().draw_mermaid())
except Exception as e:
    print(f'Display error!: {e}')
finally:
    print("--------END---------")
    print("\n")