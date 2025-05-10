from dotenv import load_dotenv
load_dotenv()
from psycopg_pool import ConnectionPool

from langgraph.checkpoint.postgres import PostgresSaver

from presentation.terminal import TerminalInterface
from infra.db import DBConnectionHandler

THREAD_ID = "main_short_term_memory"

if __name__ == '__main__':
    db = DBConnectionHandler()
    db.initialize_db()

    terminal = TerminalInterface()
    terminal.initialize_terminal(THREAD_ID)

