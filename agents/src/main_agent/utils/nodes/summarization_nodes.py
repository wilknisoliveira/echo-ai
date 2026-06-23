"""Summarization node configuration and factory utilities."""

from langchain_core.messages import RemoveMessage
from langchain_core.prompts import ChatPromptTemplate
from langmem.short_term import SummarizationNode

from main_agent.utils.state import State

DEFAULT_SUMMARIZATION_GUIDE = (
    "When summarizing, preserve timestamps for key events or milestones "
    "if they are relevant to the conversation context. Only include "
    "timestamps when they add meaningful temporal context."
)


def _make_guide_prompts(guide: str | None) -> dict:
    """Build prompt templates that include the guide if provided."""
    if not guide:
        return {}

    return {
        "initial_summary_prompt": ChatPromptTemplate.from_messages([
            ("placeholder", "{messages}"),
            ("user", f"{guide}\n\nCreate a summary of the conversation above:"),
        ]),
        "existing_summary_prompt": ChatPromptTemplate.from_messages([
            ("placeholder", "{messages}"),
            (
                "user",
                f"{guide}\n\n"
                "This is summary of the conversation so far: {existing_summary}\n\n"
                "Extend this summary by taking into account the new messages above:",
            ),
        ]),
    }


def create_summarization_node(
    *,
    model,
    max_tokens: int = 10000,
    max_summary_tokens: int = 3000,
    max_tokens_before_summary: int | None = 9500,
    summary_guide: str | None = None,
) -> SummarizationNode:
    """Create a configured SummarizationNode with optional timestamp guide."""
    prompts = _make_guide_prompts(summary_guide)
    return SummarizationNode(
        model=model,
        max_tokens=max_tokens,
        max_summary_tokens=max_summary_tokens,
        max_tokens_before_summary=max_tokens_before_summary,
        output_messages_key="messages",
        **prompts,
    )


def select_messages_before_summarize(state: State):
    """Select Messages before Summarize"""
    messages_to_keep = state["messages"][-10:]
    delete_messages = [RemoveMessage(id=m.id) for m in messages_to_keep]

    return {"messages_to_keep": messages_to_keep, "messages": delete_messages}


def select_messages_after_summarize(state: State):
    """Select Messages after Summarize"""
    return {"messages_to_keep": [], "messages": state["messages_to_keep"]}
