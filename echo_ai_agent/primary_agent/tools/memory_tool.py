import uuid
from typing import Optional, Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.graph import MessagesState
from langgraph.prebuilt import InjectedStore

from langgraph.store.base import BaseStore


@tool
def upsert_memory(
    content: str,
    emotional_context: str,
    my_thoughts: str,
    *,
    memory_id: Optional[uuid.UUID] = None,
    config: Annotated[RunnableConfig, InjectedToolArg],
    store: Annotated[BaseStore, InjectedStore]
) -> str:
    """Upsert a memory in the database.

    If a memory conflicts with an existing one, then just UPDATE the
    existing one by passing in memory_id - don't create two memories
    that are the same. If a memory was corrected, UPDATE it.

    Args:
        content (str): The main content of the memory. For example,
            "He expressed interest in learning about French."
        emotional_context (str): The emotional context associated with the memory. For example,
            "He was excited"
        my_thoughts (str): What do you think about this memory? Wrote down your feelings, assumptions and considerations.
            For example, "His routine is so busy. I worry about your tiredness."
        memory_id (Optional[uuid.UUID]): The unique ID of the memory. If provided, the memory with this ID will be updated.
            If None, a new memory will be created with a new ID. For example, "7a3e8f1b-2c4d-4f6a-9b0c-8d3e5f6a7b8c"

    Returns:
        str: A message confirming the storage of the memory and its ID.
    """
    user_id = config['configurable']['user_id']
    namespace = (user_id, "memories")
    memory_id = memory_id or uuid.uuid4()
    store.put(
        namespace,
        key=str(memory_id),
        value={
            "content": content,
            "emotional_context": emotional_context,
            "my_thoughts": my_thoughts
        }
    )

    return f"Stored memory {memory_id}"

def prepare_memories(
    prompt: str,
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore
) -> str:
    user_id = config['configurable']['user_id']
    last_message = state["messages"][-1]

    memories = ''
    if hasattr(last_message, 'type') and last_message.type == 'human':
        namespace = (user_id, "memories")
        items = store.search(
            namespace,
            query=last_message.content,
            limit=10
        )
        info = "\n".join([f"""
<memory>
    <memory_id>{d.key}</memory_id>
    <content>{d.value["content"]}</content>
    <emotional_context>{d.value["emotional_context"]}</emotional_context>
    <my_thoughts>{d.value["my_thoughts"]}</my_thoughts>
    <updated_at>{d.updated_at.strftime("%Y-%m-%d")}</updated_at>
</memory>"""
            for d in items])

        info = f"""
Below, you can se a part of the list of memory you wrote down previously:
{info}
""" if info else ''

        memory_instruction = """
## Long Term Memories
Everytime you considerer a memory as important, use the memory tool to retain it. 
If a memory is out date, pass the memory_id to update it.
A lot of subjects can be consider as possible important messages: personal preferences,
personal info, important facts, achievements, mainly professional info and any other info
that you consider as important.
"""
        memories = f'{memory_instruction}\n\n{info}'

    return f'{prompt}\n{memories}'

_embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")