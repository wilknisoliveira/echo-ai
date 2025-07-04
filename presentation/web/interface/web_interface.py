import os

import streamlit as st
from langgraph_sdk import get_sync_client

class WebInterface:
    def __init__(self, thread_id: str, user_id: str):
        self.thread_id: str = thread_id
        self.user_id: str = user_id
        self.client = get_sync_client(url=os.environ.get("LANGGRAPH_API_URL"))

    @staticmethod
    def __extract_content_from_event(event: dict) -> str | None:
        message = event.data.get("messages")
        if message:
            if isinstance(message, list):
                message = message[-1]
            if message['type'] == "ai": 
                return message['content']
        return None

    def __get_response(self, message: str, thread_id: str, config: dict):
        chunks = self.client.runs.stream(
            thread_id, "graph", 
            input= {
                "messages": [{
                    "role": "human",
                    "content": message
                }]
            }, 
            stream_mode="values", config=config)

        complete_result = ''
        for chunk in chunks:
            result = self.__extract_content_from_event(chunk)
            if result:
                complete_result += result

        return complete_result

    @staticmethod
    def __check_password():
        is_authorized = st.session_state["password"] == os.environ.get("MASTER_KEY")
        st.session_state["is_authorized"] = is_authorized
        if not is_authorized:
            st.error("Not Authorized!")

    def build_interface(self) -> None:
        if "is_authorized" not in st.session_state:
            st.session_state["is_authorized"] = False

        if not st.session_state["is_authorized"]:
           st.text_input(
               "Password: ",
               type="password",
               on_change=self.__check_password,
               key="password"
           )
        else:
            st.title("Echo")
            if "messages" not in st.session_state:
                st.session_state.messages = []

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("What is up?"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

                config = {
                    "configurable": {
                        "user_id": self.user_id
                    }
                }

                with st.chat_message("assistant"):
                    response = self.__get_response(prompt, self.thread_id, config)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                # TODO: adapt to langgraph-sdk
                """
                snapshot = self.graph.get_state(config)

                if snapshot.next:
                    if prompt.strip() == "y":
                        # Continue
                        self.graph.invoke(
                            None,
                            config
                        )
                    else:
                        self.graph.invoke(
                            {
                                "messages": [
                                    {
                                        "tool_call_id": snapshot.values["messages"][-1].tool_calls[0]["id"],
                                        "content": f"API call denied by user. Reasoning: '{prompt}'. Continue assisting, accounting for the user's input."
                                    }
                                ]
                            },
                            config
                        )
                else:
                    with st.chat_message("assistant"):
                        response = self.__get_response(prompt, config)
                        st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                snapshot = self.graph.get_state(config)
                if snapshot.next:
                    last_tool = snapshot.values["messages"][-1].tool_calls[0]
                    with st.chat_message("assistant"):
                        st.markdown("**Pending action:**")
                        st.json(
                            {
                                "Tool": last_tool["name"],
                                "Argumentos": last_tool["args"],
                                "ID": last_tool["id"]
                            }
                        )
                        st.markdown(
                            "Do you approve of the above actions? Type 'y' to continue;"
                            " otherwise, explain your requested changed.\n\n"
                        )
                    st.session_state.messages.append({"role": "assistant", "content": response})

                """
