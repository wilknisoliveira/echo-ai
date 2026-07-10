import logging
import os
from typing import Any

import streamlit as st  # type: ignore[import-not-found]
from langgraph_sdk import get_sync_client  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class WebInterface:
    def __init__(self, user_id: str, debug: bool = False):
        self.user_id: str = user_id
        self.debug: bool = debug
        self.client = get_sync_client(url=os.environ.get("LANGGRAPH_API_URL"))

    @staticmethod
    def _get_thread_title(thread: dict) -> str:
        if title := thread.get("metadata", {}).get("title"):
            return title
        messages = thread.get("values", {}).get("messages", [])
        for msg in messages:
            if msg.get("type") == "human":
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = "".join(
                        block.get("text", "")
                        for block in content
                        if block.get("type") == "text"
                    )
                if content:
                    return (content[:50] + "...") if len(content) > 50 else content
        tid = thread.get("thread_id", "")
        return tid[:8] + "..." if len(tid) > 8 else tid

    def _list_threads(self) -> list[dict[str, Any]]:
        try:
            return self.client.threads.search(  # type: ignore[return-value]
                metadata={"graph_id": "agent"},
                sort_by="updated_at",
                sort_order="desc",
                limit=50,
            )
        except Exception:
            logger.exception("Failed to list threads")
            return []

    def _create_thread(self) -> str:
        thread = self.client.threads.create(
            metadata={
                "title": "New Chat",
                "user_id": self.user_id,
            }
        )
        return thread["thread_id"]

    def _update_thread_metadata(self, thread_id: str, metadata: dict) -> None:
        try:
            self.client.threads.update(thread_id=thread_id, metadata=metadata)
        except Exception:
            logger.exception("Failed to update thread %s", thread_id)

    def _try_auto_title(self, thread_id: str) -> None:
        try:
            thread = self.client.threads.get(thread_id)
            metadata = thread.get("metadata") or {}
            if metadata.get("title") != "New Chat":
                return
        except Exception:
            return
        messages = st.session_state.get("messages") or []
        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"]
                title = (content[:50] + "...") if len(content) > 50 else content
                self._update_thread_metadata(thread_id, {"title": title})
                return

    def _switch_thread(self, thread_id: str) -> None:
        st.session_state.thread_id = thread_id
        if "messages" in st.session_state:
            del st.session_state.messages
        if "renaming" in st.session_state:
            del st.session_state.renaming

    def _load_history(self) -> None:
        try:
            state = self.client.threads.get_state(st.session_state.thread_id)
            if not isinstance(state, dict):
                return
            values = state.get("values")
            if isinstance(values, dict):
                messages = values.get("messages", [])
            else:
                messages = values if isinstance(values, list) else []
        except Exception:
            logger.warning("Could not fetch thread history for %s", st.session_state.thread_id)
            return

        for msg in messages[-20:]:
            role = msg.get("type")
            if role not in ("human", "ai"):
                continue
            content = msg.get("content", "")
            if not content:
                continue
            if isinstance(content, list):
                content = "".join(
                    block.get("text", "")
                    for block in content
                    if block.get("type") == "text"
                )
            st.session_state.messages.append({
                "role": "user" if role == "human" else "assistant",
                "content": content,
            })

    def _stream_response(self, message: str, thread_id: str, config: dict):
        status_placeholder = st.empty()

        try:
            chunks = self.client.runs.stream(  # type: ignore[call-overload]
                thread_id,
                "agent",
                input={"messages": [{"role": "human", "content": message}]},
                stream_mode=["messages-tuple", "updates"],
                config=config,
            )

            for chunk in chunks:
                if self.debug:
                    logger.debug("Streaming event: %s", chunk)

                if chunk.event == "messages":
                    message_chunk, metadata = chunk.data
                    if metadata.get("langgraph_node") == "primary_assistant":
                        content = message_chunk.get("content", "")
                        if content:
                            status_placeholder.empty()
                            yield content

                elif chunk.event == "updates":
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
            yield "\u26a0\ufe0f Erro ao processar sua mensagem. Tente novamente mais tarde."

    @staticmethod
    def __check_password():
        is_authorized = st.session_state["password"] == os.environ.get("MASTER_KEY")
        st.session_state["is_authorized"] = is_authorized
        if not is_authorized:
            st.error("Not Authorized!")

    def _render_sidebar(self) -> None:
        st.sidebar.title("Threads")

        if st.sidebar.button("+ New Thread", use_container_width=True, key="new_thread_btn"):
            new_id = self._create_thread()
            self._switch_thread(new_id)
            st.rerun()

        st.sidebar.divider()

        threads = self._list_threads()

        if not threads:
            st.sidebar.info("No conversations yet.")
            return

        for thread in threads:
            tid = thread["thread_id"]
            title = self._get_thread_title(thread)
            is_active = tid == st.session_state.thread_id

            col1, col2 = st.sidebar.columns([5, 1])
            with col1:
                btn_label = f"{'📍' if is_active else '💬'} {title}"
                if st.button(btn_label, key=f"thread_{tid}", use_container_width=True):
                    if not is_active:
                        self._switch_thread(tid)
                        st.rerun()
            with col2:
                if st.button("✏️", key=f"edit_{tid}"):
                    st.session_state.renaming = tid
                    st.rerun()

            if st.session_state.get("renaming") == tid:
                with st.sidebar.container():
                    new_title = st.text_input("Title:", value=title, key=f"rename_input_{tid}")
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.button("Save", key=f"save_{tid}", use_container_width=True):
                            self._update_thread_metadata(tid, {"title": new_title})
                            st.session_state.renaming = None
                            st.rerun()
                    with sc2:
                        if st.button("Cancel", key=f"cancel_{tid}", use_container_width=True):
                            st.session_state.renaming = None
                            st.rerun()

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
            if "thread_id" not in st.session_state:
                threads = self._list_threads()
                if threads:
                    st.session_state.thread_id = threads[0]["thread_id"]
                else:
                    st.session_state.thread_id = self._create_thread()

            self._render_sidebar()

            st.title("Echo")
            if "messages" not in st.session_state:
                st.session_state.messages = []
                self._load_history()

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("What is up?"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

                config = {"configurable": {"user_id": self.user_id}}

                with st.chat_message("assistant"):
                    response = st.write_stream(self._stream_response(prompt, st.session_state.thread_id, config))
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )

                self._try_auto_title(st.session_state.thread_id)
