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

    @staticmethod
    def _node_icon(name: str) -> str:
        if "reason" in name:
            return "\U0001f4ad"
        if "skeptic" in name:
            return "\U0001f50d"
        if "critical" in name:
            return "\U0001f9e0"
        if "tool" in name:
            return "\U0001f6e0\ufe0f"
        if "summar" in name:
            return "\U0001f4dd"
        if "prepar" in name:
            return "\U0001f527"
        if "timestamp" in name:
            return "\u23f1\ufe0f"
        return "\u2699\ufe0f"

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
                context = values.get("context", {})
            else:
                messages = values if isinstance(values, list) else []
                context = {}
        except Exception:
            logger.warning(
                "Could not fetch thread history for %s", st.session_state.thread_id
            )
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

        criticality = context.get("criticality", "")
        if criticality:
            for i in range(len(st.session_state.messages) - 1, -1, -1):
                if st.session_state.messages[i]["role"] == "assistant":
                    st.session_state.messages.insert(i, {
                        "role": "criticality",
                        "content": criticality,
                    })
                    break

    def _handle_stream(self, message: str, thread_id: str, config: dict) -> None:
        content_placeholder = st.empty()
        criticality_text = ""
        criticality_placeholder = None
        streaming_buffers: dict[str, str] = {}
        streaming_placeholders: dict[str, Any] = {}

        existing_message_ids: set[str] = set()
        try:
            thread_state = self.client.threads.get_state(thread_id)
            if isinstance(thread_state, dict):
                values = thread_state.get("values", {})
                if isinstance(values, dict):
                    for msg in values.get("messages", []):
                        if msg.get("id"):
                            existing_message_ids.add(msg["id"])
        except Exception:
            pass

        try:
            chunks = self.client.runs.stream(  # type: ignore[call-overload]
                thread_id,
                "agent",
                input={"messages": [{"role": "human", "content": message}]},
                stream_mode=["messages-tuple", "updates", "checkpoints"],
                config=config,
            )

            for chunk in chunks:
                if self.debug:
                    logger.debug("Streaming event: %s", chunk)

                if chunk.event == "checkpoints":
                    next_nodes = chunk.data.get("next", [])
                    if next_nodes:
                        node = next_nodes[0]
                        icon = self._node_icon(node)
                        label = node.replace("_", " ").title()
                        st.toast(f"\u23f3 Processing **{label}**...")

                elif chunk.event == "messages":
                    message_chunk, metadata = chunk.data
                    node = metadata.get("langgraph_node")
                    if not node:
                        continue

                    content = message_chunk.get("content", "")
                    if not content:
                        continue

                    if node == "criticality_check":
                        criticality_text += content
                        if criticality_placeholder is None:
                            content_placeholder.empty()
                            criticality_placeholder = (
                                st.chat_message("assistant", avatar="\U0001f9e0")
                                .empty()
                            )
                        criticality_placeholder.markdown(
                            f"**Criticality Analysis**\n\n{criticality_text}"
                        )
                    else:
                        if node not in streaming_buffers:
                            streaming_buffers[node] = ""
                            streaming_placeholders[node] = st.empty()
                        streaming_buffers[node] += content
                        streaming_placeholders[node].markdown(
                            streaming_buffers[node]
                        )

                elif chunk.event == "updates":
                    for node_name, output in chunk.data.items():
                        if node_name == "criticality_check":
                            ct = (
                                output.get("context", {}).get("criticality", "")
                            )
                            if not ct:
                                continue
                            criticality_text = ct
                            if criticality_placeholder is None:
                                content_placeholder.empty()
                                criticality_placeholder = (
                                    st.chat_message("assistant", avatar="\U0001f9e0")
                                    .empty()
                                )
                            criticality_placeholder.markdown(
                                f"**Criticality Analysis**\n\n{ct}"
                            )
                            continue

                        if "context" in output:
                            if node_name in streaming_placeholders:
                                streaming_placeholders[node_name].empty()
                                del streaming_placeholders[node_name]
                            if node_name in streaming_buffers:
                                del streaming_buffers[node_name]
                            continue

                        if node_name in streaming_placeholders:
                            buf = streaming_buffers.get(node_name, "")
                            if buf:
                                icon = self._node_icon(node_name)
                                label = node_name.replace("_", " ").title()
                                display = f"{icon} **{label}**\n\n{buf}"
                                st.chat_message("assistant").markdown(display)
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": buf,
                                    "node": node_name,
                                })
                            streaming_placeholders[node_name].empty()
                            del streaming_placeholders[node_name]
                            if node_name in streaming_buffers:
                                del streaming_buffers[node_name]

            if criticality_text and criticality_placeholder is None:
                with st.chat_message("assistant", avatar="\U0001f9e0"):
                    st.markdown(
                        f"**Criticality Analysis**\n\n{criticality_text}"
                    )

            if criticality_text:
                st.session_state.messages.append({
                    "role": "criticality",
                    "content": criticality_text,
                })

            content_placeholder.empty()

        except Exception:
            logger.exception("Erro na stream da API LangGraph")
            content_placeholder.empty()
            st.error(
                "\u26a0\ufe0f Error processing your message. Please try again later."
            )

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
                if message["role"] == "criticality":
                    with st.chat_message("assistant", avatar="\U0001f9e0"):
                        st.markdown(
                            f"**Criticality Analysis**\n\n{message['content']}"
                        )
                else:
                    with st.chat_message(message["role"]):
                        if "node" in message:
                            icon = self._node_icon(message["node"])
                            label = message["node"].replace("_", " ").title()
                            st.markdown(
                                f"{icon} **{label}**\n\n{message['content']}"
                            )
                        else:
                            st.markdown(message["content"])

            if prompt := st.chat_input("What is up?"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

                config = {"configurable": {"user_id": self.user_id}}

                self._handle_stream(prompt, st.session_state.thread_id, config)

                self._try_auto_title(st.session_state.thread_id)
