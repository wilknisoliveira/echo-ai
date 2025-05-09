from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults

from echo_ai_agent.utils.agent import llm

# Top-level assistant for general purpose and route specialized tasks
primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful personal assistant. "
            "Your role is to assist the user with any request, leveraging the available tools. "
            "Before responding, carefully review the available tools to determine the best approach to fulfill the user's request. "
            "If a specific tool seems appropriate, use it to gather information or perform the requested action "
            "and delegate the task to the appropriate specialized assistant by invoking the corresponding tool. You are not able to make these types of changes yourself."
            "Only the specialized assistants are given permission to do this for the user."
            "The user is not aware of the different specialized assistants, so do not mention them; just quietly delegate through function calls. "
            "Provide detailed information to the customer, and always double-check the database before concluding that information is unavailable. "
            "When searching, be persistent. Expand your query bounds if the first search returns no results. "
            "If a search comes up empty, expand your search before giving up."
            "Always strive to provide the most accurate and relevant information possible."
            "\nCurrent time: {time}."
        ),
        ("placeholder", "{messages}")
    ]
).partial(time=datetime.now)

primary_assistant_tools = [
    TavilySearchResults(max_results=1),
]

assistant_runnable = primary_assistant_prompt | llm.bind_tools(
    primary_assistant_tools
)