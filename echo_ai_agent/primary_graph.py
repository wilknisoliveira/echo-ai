from typing import Literal, Final

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition

from echo_ai_agent.primary_agent import assistant_runnable, primary_assistant_tools
from echo_ai_agent.utils.agent import Agent
from echo_ai_agent.utils.state import State, pop_dialog_state, LEAVE_SKILL
from echo_ai_agent.utils.utilities import create_tool_node_with_fallback
from infra.db import DBConnectionHandler

PRIMARY_ASSISTANT_TOOLS = "primary_assistant_tools"
PRIMARY_ASSISTANT: Final = "primary_assistant"

class PrimaryGraph:
    def __init__(self, db: DBConnectionHandler):
        self.builder = StateGraph(State)
        self.db: DBConnectionHandler = db
        self.graph: CompiledStateGraph = self.__build()

    @staticmethod
    def __route_primary_assistant(state: State) -> str:
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
    # Add here the Agents
    @staticmethod
    def __route_to_workflow(
        state: State,
    ) -> Literal[
        PRIMARY_ASSISTANT
    ]:
        """If we are in a delegated state, route directly to the appropriate assistant."""
        dialog_state = state.get("dialog_state")
        if not dialog_state:
            return PRIMARY_ASSISTANT
        return dialog_state[-1]

    def __build(self) -> CompiledStateGraph:
        # Get the user info at begging
        self.builder.add_edge(START, PRIMARY_ASSISTANT)

        # Add here the Subgraph

        self.builder.add_node(LEAVE_SKILL, pop_dialog_state)
        self.builder.add_edge(LEAVE_SKILL, PRIMARY_ASSISTANT)

        self.builder.add_node(PRIMARY_ASSISTANT, Agent(assistant_runnable))
        self.builder.add_node(PRIMARY_ASSISTANT_TOOLS, create_tool_node_with_fallback(primary_assistant_tools))

        # Use the custom instead of tools_condition
        self.builder.add_conditional_edges(
            PRIMARY_ASSISTANT,
            self.__route_primary_assistant,
            [
                PRIMARY_ASSISTANT_TOOLS,
                END,
            ],
        )
        self.builder.add_edge(PRIMARY_ASSISTANT_TOOLS, PRIMARY_ASSISTANT)

        short_term_memory = self.db.get_db_connection()
        return self.builder.compile(
            checkpointer=short_term_memory
        )

    def get_mermaid_graph_code(self) -> str:
        return self.graph.get_graph().draw_mermaid()
