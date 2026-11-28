import os

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row


def database_url():
    if url := os.getenv("DATABASE_URL"):
        return url
    return make_conninfo(
        host=os.getenv("PGHOST", "postgres"),
        dbname="ideas",
        user="app",
        password=os.environ["POSTGRES_PASSWORD"],
    )


def connect():
    return psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=5)
