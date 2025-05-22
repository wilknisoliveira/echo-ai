import os

from dotenv import load_dotenv
from langgraph.graph.state import CompiledStateGraph
from streamlit import cache_resource

from echo_ai_agent.tools.memory_tool import get_store_index
from presentation.web.web_interface import WebInterface

load_dotenv()

from echo_ai_agent.primary_graph import PrimaryGraph
from presentation.terminal import TerminalInterface
from infra.db import DBConnectionHandler

THREAD_ID = "main_short_term_memory"
USER_ID = "main_profile"

@cache_resource
def initialize_system() -> CompiledStateGraph:
    # Initialize db connection
    store_index = get_store_index()
    db = DBConnectionHandler(os.environ["DB_URI"], store_index)
    db.initialize_db()

    # Initialize the primary graph
    primary_graph = PrimaryGraph(db)

    print("Graph Mermaid Code")
    print("--------START---------")
    try:
        print(primary_graph.get_mermaid_graph_code())
    except Exception as e:
        print(f'Display error!: {e}')
    finally:
        print("--------END---------")
        print("\n")

    return primary_graph.graph

if __name__ == '__main__':
    graph = initialize_system()

    web_interface = WebInterface(graph, THREAD_ID, USER_ID)
    web_interface.build_interface()

    # Initialize Terminal Interface
    # terminal = TerminalInterface(graph)
    # terminal.initialize_terminal(THREAD_ID, USER_ID)

