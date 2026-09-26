import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
    if url.startswith("postgresql+psycopg://"):
        return url
    raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection URL")


SQLALCHEMY_DATABASE_URL = get_database_url()

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
