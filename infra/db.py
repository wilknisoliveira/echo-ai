import os
from psycopg_pool import ConnectionPool

from langgraph.checkpoint.postgres import PostgresSaver

class DBConnectionHandler:
    def __init__(self):
        self.DB_URI = os.environ["DB_URI"]
        self.pool = ConnectionPool(
            conninfo=self.DB_URI,
            min_size=5,
            max_size=20,
            timeout=30
        )

    def initialize_db(self) -> None:
        with self.pool.connection() as conn:
            conn.autocommit = True
            short_term_memory = PostgresSaver(conn)
            short_term_memory.setup()

    def get_db_connection(self) -> PostgresSaver:
        return PostgresSaver(self.pool)

    def close_connection_pool(self) -> None:
        self.pool.close()
