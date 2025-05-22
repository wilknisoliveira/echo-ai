from langgraph.store.postgres import PostgresStore
from langgraph.store.postgres.base import PostgresIndexConfig
from psycopg_pool import ConnectionPool

from langgraph.checkpoint.postgres import PostgresSaver

class DBConnectionHandler:
    def __init__(self, db_uri: str, index: PostgresIndexConfig):
        self.DB_URI = db_uri
        self.pool = ConnectionPool(
            conninfo=self.DB_URI,
            min_size=5,
            max_size=20,
            timeout=30
        )
        self.index: PostgresIndexConfig = index

    def initialize_db(self) -> None:
        with self.pool.connection() as conn:
            conn.autocommit = True
            short_term_memory = PostgresSaver(conn)
            short_term_memory.setup()

            long_term_memory = PostgresStore(
                conn,
                index=self.index
            )
            long_term_memory.setup()

    def get_db_connection(self) -> (PostgresSaver, PostgresStore):
        return PostgresSaver(self.pool), PostgresStore(
            self.pool,
            index=self.index
        )

    def close_connection_pool(self) -> None:
        self.pool.close()
