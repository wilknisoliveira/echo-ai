from datetime import datetime

from main_agent.utils.state import State


def attach_timestamps(state: State) -> dict:
    """Attach current timestamp to the newest human message missing one."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for m in reversed(state["messages"]):
        if m.type == "human" and m.content and not m.content.startswith("["):
            m.content = f"[{now}] {m.content}"
            break
    return {"messages": state["messages"]}
