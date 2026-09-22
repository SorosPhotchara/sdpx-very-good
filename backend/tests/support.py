"""Isolated PostgreSQL schemas for database tests."""

import os
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app import models


class TestDatabase:
    __test__ = False

    def __init__(self) -> None:
        url = os.environ.get("TEST_DATABASE_URL", "")
        if not url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("Set TEST_DATABASE_URL to a disposable PostgreSQL database")
        self.schema = "test_" + uuid4().hex
        self.admin = create_engine(url)
        with self.admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.engine: Engine = create_engine(
            url, connect_args={"options": f"-csearch_path={self.schema},public"}
        )
        try:
            # Public tables may already exist; always create a fresh copy in the
            # test schema instead of accepting tables later in search_path.
            models.Base.metadata.create_all(self.engine, checkfirst=False)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        self.engine.dispose()
        with self.admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE'))
        self.admin.dispose()
