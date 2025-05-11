from dotenv import load_dotenv

from presentation.web.web_interface import WebInterface

load_dotenv()

from echo_ai_agent.primary_graph import PrimaryGraph
from presentation.terminal import TerminalInterface
from infra.db import DBConnectionHandler

THREAD_ID = "main_short_term_memory"

if __name__ == '__main__':
    # Initialize db connection
    db = DBConnectionHandler()
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

    web_interface = WebInterface(primary_graph.graph, THREAD_ID)
    web_interface.build_interface()

    # Initialize Terminal Interface
    #terminal = TerminalInterface(primary_graph.graph)
    #terminal.initialize_terminal(THREAD_ID)

