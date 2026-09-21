"""Prepare and run the local backend used by Playwright."""

import os

os.environ["APP_ENV"] = "development"
os.environ["AUTH_MODE"] = "mock"
os.environ["INSTRUCTOR_EMAILS"] = "teacher@example.edu"
os.environ["FRONTEND_ORIGINS"] = "http://127.0.0.1:5173"
base_url = os.environ.get("E2E_DATABASE_URL", "postgresql+psycopg://paireval@127.0.0.1:5433/paireval")

from sqlalchemy import create_engine, text

with create_engine(base_url).begin() as connection:
    connection.execute(text("DROP SCHEMA IF EXISTS paireval_e2e CASCADE"))
    connection.execute(text("CREATE SCHEMA paireval_e2e"))
os.environ["DATABASE_URL"] = f"{base_url}?options=-csearch_path%3Dpaireval_e2e"

from alembic import command
from alembic.config import Config
import uvicorn

from seed_demo import seed

command.upgrade(Config("alembic.ini"), "head")
seed()
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
