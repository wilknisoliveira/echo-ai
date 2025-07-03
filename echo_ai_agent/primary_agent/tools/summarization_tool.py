from langchain_core.messages import RemoveMessage
from primary_agent.utils.state import State


def select_messages_before_summarize(
    state: State
):
    """Select Messages before Summarize"""
    messages_to_keep = state['messages'][-10:]
    delete_messages = [RemoveMessage(id=m.id) for m in messages_to_keep]

    return {
        "messages_to_keep": messages_to_keep,
        "messages": delete_messages
    }

def select_messages_after_summarize(
    state: State
):
    """Select Messages after Summarize"""

    return {
        "messages_to_keep": [],
        "messages": state["messages_to_keep"]
    }