from langchain_core.messages import ToolMessage
from langgraph.graph import MessagesState
from typing_extensions import Literal
from typing import Annotated, Optional, Any

from langgraph.graph.message import AnyMessage, add_messages

class DialogManager:
    LEAVE_SKILL = "leave_skill"

    @staticmethod
    def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
        """Push or pop the state"""
        if right is None:
            return left
        if right == "pop":
            return left[:-1]
        return left + [right]

    @staticmethod
    def pop_dialog_state(state: dict) -> dict:
        """Pop the dialog stack and return to the main assistant.

        This lets the full graph explicitly track the dialog flow and delegate control
        to specific sub-graphs.
        """
        messages = []
        if state["messages"][-1].tool_calls:
            messages.append(
                ToolMessage(
                    content="Resuming dialog with the host assistant. Please reflect on the past conversation and assist the user as needed.",
                    tool_call_id=state["messages"][-1].tool_calls[0]["id"]
                )
            )
        return {
            "dialog_state": "pop",
            "messages": messages
        }

class State(MessagesState):
    context: dict[str, Any]
    dialog_state: Annotated[
        list[
            Literal[
                "assistant",
                "update_flight",
                "book_car_rental",
                "book_hotel",
                "book_excursion"
            ]
        ],
        DialogManager().update_dialog_stack
    ]