from typing import Literal, Final

from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition
from langmem.short_term import SummarizationNode

from primary_agent.primary_agent import PrimaryAgent
from primary_agent.tools.summarization_tool import select_messages_before_summarize, select_messages_after_summarize
from primary_agent.utils.agent import Agent
from primary_agent.utils.state import State, DialogManager
from primary_agent.utils.node_manager import NodeManager
from primary_agent.utils.llm_model import LLMModel


class PrimaryGraph:
    PRIMARY_ASSISTANT_TOOLS = "primary_assistant_tools"
    PRIMARY_ASSISTANT: Final = "primary_assistant"
    SELECT_MESSAGES_BEFORE_SUMMARIZE = "select_messages_before_summarize"
    SELECT_MESSAGES_AFTER_SUMMARIZE = "select_messages_after_summarize"
    SUMMARIZE = "summarize"

    def __init__(self):
        self.builder = StateGraph(State)
        self.primary_agent = PrimaryAgent()
        self.node_manager = NodeManager()
        self.dialog_manager = DialogManager()
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
            return PrimaryGraph.PRIMARY_ASSISTANT_TOOLS
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
            return PrimaryGraph.PRIMARY_ASSISTANT
        return dialog_state[-1]

    def __build(self) -> CompiledStateGraph:
        summarization_node = SummarizationNode(
            token_counter=count_tokens_approximately,
            model=LLMModel(max_tokens=3000).llm,
            max_summary_tokens=3000,
            max_tokens=10000,
            max_tokens_before_summary=9500, # Less than max_tokens to avoid loss data
            output_messages_key="messages"
        )

        self.builder.add_node(PrimaryGraph.SELECT_MESSAGES_BEFORE_SUMMARIZE, select_messages_before_summarize)
        self.builder.add_node(PrimaryGraph.SUMMARIZE, summarization_node)
        self.builder.add_node(PrimaryGraph.SELECT_MESSAGES_AFTER_SUMMARIZE, select_messages_after_summarize)
        self.builder.add_node(PrimaryGraph.PRIMARY_ASSISTANT, Agent(self.primary_agent.assistant_runnable))
        self.builder.add_node(
            PrimaryGraph.PRIMARY_ASSISTANT_TOOLS,
            self.node_manager.create_tool_node_with_fallback(self.primary_agent.primary_assistant_tools)
        )
        self.builder.add_node(DialogManager.LEAVE_SKILL, DialogManager.pop_dialog_state)

        self.builder.add_edge(START, PrimaryGraph.SELECT_MESSAGES_BEFORE_SUMMARIZE)
        self.builder.add_edge(PrimaryGraph.SELECT_MESSAGES_BEFORE_SUMMARIZE, PrimaryGraph.SUMMARIZE)
        self.builder.add_edge(PrimaryGraph.SUMMARIZE, PrimaryGraph.SELECT_MESSAGES_AFTER_SUMMARIZE)
        self.builder.add_edge(PrimaryGraph.SELECT_MESSAGES_AFTER_SUMMARIZE, PrimaryGraph.PRIMARY_ASSISTANT)
        self.builder.add_conditional_edges(
            PrimaryGraph.PRIMARY_ASSISTANT,
            self.__route_primary_assistant,
            [
                PrimaryGraph.PRIMARY_ASSISTANT_TOOLS,
                END,
            ],
        )
        self.builder.add_edge(PrimaryGraph.PRIMARY_ASSISTANT_TOOLS, PrimaryGraph.PRIMARY_ASSISTANT)
        self.builder.add_edge(DialogManager.LEAVE_SKILL, PrimaryGraph.PRIMARY_ASSISTANT)

        return self.builder.compile()

    def get_mermaid_graph_code(self) -> str:
        return self.graph.get_graph().draw_mermaid()


primary_graph = PrimaryGraph()
graph = primary_graph.graph
