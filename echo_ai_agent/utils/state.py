from langchain_core.messages import ToolMessage
from typing_extensions import TypedDict, Literal
from typing import Annotated, Optional

from langgraph.graph.message import AnyMessage, add_messages

LEAVE_SKILL = "leave_skill"

def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop the state"""
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]

# User info is used to pass custom params, as user confirmation or passenger_id
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_info: str
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
        update_dialog_stack
    ]

def pop_dialog_state(state: State) -> dict:
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