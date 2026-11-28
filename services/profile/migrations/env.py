import psycopg
from alembic import context
from sqlalchemy import create_engine

from foundation import database_url

engine = create_engine(
    "postgresql+psycopg://", creator=lambda: psycopg.connect(database_url())
)
with engine.connect() as connection:
    context.configure(connection=connection, transactional_ddl=True)
    with context.begin_transaction():
        context.run_migrations()
