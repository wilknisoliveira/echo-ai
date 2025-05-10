from langchain_core.messages import ToolMessage
from langgraph.graph.state import CompiledStateGraph


class TerminalInterface:
    def __init__(self, graph: CompiledStateGraph):
        self.graph: CompiledStateGraph = graph

    @staticmethod
    def print_event(event: dict, _printed: set, max_length=1500):
        current_state = event.get("dialog_state")
        if current_state:
            print("Currently in: ", current_state[-1])
        message = event.get("messages")
        if message:
            if isinstance(message, list):
                message = message[-1]
            if message.id not in _printed:
                msg_repr = message.pretty_repr(html=True)
                if len(msg_repr) > max_length:
                    msg_repr = msg_repr[:max_length] + "... (truncated)"
                print(msg_repr)

                _printed.add(message.id)

    def initialize_terminal(self, thread_id: str) -> None:
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        _printed = set()

        while True:
            question: str = input("\n\nUser input: ")

            if question.lower() == 'close':
                print("See you!")
                break

            events = self.graph.stream(
                {"messages": ("user", question)},
                config,
                stream_mode="values"
            )
            for event in events:
                self.print_event(event, _printed)

            snapshot = self.graph.get_state(config)
            while snapshot.next:
                try:
                    user_input = input(
                        "Do you approve of the above actions? Type 'y' to continue;"
                        " otherwise, explain your requested changed.\n\n"
                    )
                except:
                    user_input = "y"

                if user_input.strip() == "y":
                    # Continue
                    self.graph.invoke(
                        None,
                        config
                    )
                else:
                    self.graph.invoke(
                        {
                            "messages": [
                                ToolMessage(
                                    tool_call_id=event["messages"][-1].tool_calls[0]["id"],
                                    content=f"API call denied by user. Reasoning: '{user_input}'. Continue assisting, accounting for the user's input."
                                )
                            ]
                        },
                        config
                    )
                snapshot = self.graph.get_state(config)