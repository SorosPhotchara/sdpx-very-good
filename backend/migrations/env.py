import os

from alembic import context
from sqlalchemy import create_engine, pool

from app import models  # Registers ORM tables on Base.metadata.
from app.database import Base, get_database_url

target_metadata = Base.metadata


def migration_url() -> str:
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("Set DATABASE_URL explicitly before running migrations")
    return get_database_url()


def run_migrations_offline() -> None:
    context.configure(
        url=migration_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with create_engine(migration_url(), poolclass=pool.NullPool).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
