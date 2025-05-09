from langchain_core.messages import ToolMessage

from echo_ai_agent.primary_graph import graph
from echo_ai_agent.utils.utilities import print_event


class TerminalInterface:
    def __init__(self):
        pass

    @staticmethod
    def initialize_terminal(thread_id: str) -> None:
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

            events = graph.stream(
                {"messages": ("user", question)},
                config,
                stream_mode="values"
            )
            for event in events:
                print_event(event, _printed)

            snapshot = graph.get_state(config)
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
                    graph.invoke(
                        None,
                        config
                    )
                else:
                    graph.invoke(
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
                snapshot = graph.get_state(config)