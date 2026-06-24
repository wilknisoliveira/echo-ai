import logging
import os

import streamlit as st
from langgraph_sdk import get_sync_client

logger = logging.getLogger(__name__)


class WebInterface:
    def __init__(self, thread_id: str, user_id: str, debug: bool = False):
        self.thread_id: str = thread_id
        self.user_id: str = user_id
        self.debug: bool = debug
        self.client = get_sync_client(url=os.environ.get("LANGGRAPH_API_URL"))

    def __get_response(self, message: str, thread_id: str, config: dict) -> str:
        status_placeholder = st.empty()
        result = ""

        try:
            chunks = self.client.runs.stream(
                thread_id,
                "agent",
                input={"messages": [{"role": "human", "content": message}]},
                stream_mode="updates",
                config=config,
            )

            for chunk in chunks:
                if self.debug:
                    logger.debug("Streaming event: %s", chunk)

                for node_name, output in chunk.data.items():
                    if node_name == "primary_assistant":
                        messages = output.get("messages", [])
                        if messages and isinstance(messages, list):
                            last_msg = messages[-1]
                            if last_msg.get("type") == "ai":
                                tool_calls = last_msg.get("tool_calls", [])
                                if tool_calls:
                                    tool_name = tool_calls[0].get("name", "ferramenta")
                                    status_placeholder.markdown(f"\u2699\ufe0f Executando {tool_name}...")
                                else:
                                    content = last_msg.get("content", "")
                                    if isinstance(content, list):
                                        result = "".join(
                                            block.get("text", "")
                                            for block in content
                                            if block.get("type") == "text"
                                        )
                                    else:
                                        result = content or ""
                                    status_placeholder.empty()
                    elif node_name == "criticality_check":
                        status_placeholder.markdown("\u2699\ufe0f Executando criticality_agent...")
                    elif node_name == "summarize":
                        status_placeholder.markdown("\u2699\ufe0f Compactando hist\u00f3rico...")
                    elif node_name == "primary_assistant_tools":
                        status_placeholder.markdown("\u2699\ufe0f Executando ferramenta...")
                    elif node_name in (
                        "attach_timestamps",
                        "select_messages_before_summarize",
                        "select_messages_after_summarize",
                    ):
                        status_placeholder.markdown("\u2699\ufe0f Processando...")
        except Exception:
            logger.exception("Erro na stream da API LangGraph")
            status_placeholder.empty()
            return "\u26a0\ufe0f Erro ao processar sua mensagem. Tente novamente mais tarde."

        return result

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
                key="password",
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

                config = {"configurable": {"user_id": self.user_id}}

                with st.chat_message("assistant"):
                    response = self.__get_response(prompt, self.thread_id, config)
                    st.markdown(response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )

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
