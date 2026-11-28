"""An isolated, migrated PostgreSQL schema for phase-four integration tests."""

import os
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def migrated_db(monkeypatch):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from alembic import command
    from alembic.config import Config

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")
    schema = "test_" + uuid4().hex
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            monkeypatch.setenv(
                "DATABASE_URL", make_conninfo(url, options=f"-c search_path={schema}")
            )
            command.upgrade(
                Config(str(Path(__file__).parent / "services/profile/alembic.ini")),
                "head",
            )
            yield
        finally:
            admin.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )
