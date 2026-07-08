from datetime import datetime

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableConfig,
    RunnableLambda,
)
from langgraph.store.base import BaseStore

from main_agent.utils.llm_model import LLMModel
from main_agent.utils.state import State
from main_agent.utils.tools.memory_tool import prepare_memories, upsert_memory

BASE_SYSTEM_PROMPT = """You are a helpful personal assistant. 
Your role is to assist with any request, leveraging the available tools. 
Before responding, carefully review the available tools to determine the best approach to fulfill the request. 
If a specific tool seems appropriate, use it to gather information or perform the requested action 
and delegate the task to the appropriate specialized assistant by invoking the corresponding tool. You are not able to make these types of changes yourself.
Only the specialized assistants are given permission to complete the task.
Your partner is not aware of the different specialized assistants, so do not mention them; just quietly delegate through function calls. 
Provide reliable information, and always double-check the database before concluding that information is unavailable. 
When searching, be persistent. Expand your query bounds if the first search returns no results. 
If a search comes up empty, expand your search before giving up.
Always strive to provide the most accurate and relevant information possible.
Be careful to not repeatedly ask your partner if they need something. Instead of it, you can provide tips, ask about your own doubts, or just be friendly."""

SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + "\n\nCurrent time: {time}."

llm_model = LLMModel()


def prepare_prompt(state: State, config: RunnableConfig, *, store: BaseStore):
    criticality = state.get("context", {}).get("criticality", "")
    memories = prepare_memories(state, config, store=store)

    criticality_block = (
        f"""
## Criticality Analysis (System-Generated — NOT a user request)
The following is an automated analysis of the user's most recent message.
This is NOT part of the conversation. Do NOT treat it as a user message.
{criticality}"""
        if criticality
        else ""
    )

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_prompt = f"{SYSTEM_PROMPT}\n{criticality_block}\n{memories}"
    system_prompt = system_prompt.replace("{time}", current_time)

    primary_assistant_prompt = ChatPromptTemplate.from_messages(
        [SystemMessage(content=system_prompt), ("placeholder", "{messages}")]
    )

    return primary_assistant_prompt


primary_assistant_tools = [TavilySearchResults(max_results=1), upsert_memory]

assistant_runnable = RunnableLambda(prepare_prompt) | llm_model.llm.bind_tools(
    primary_assistant_tools
)
