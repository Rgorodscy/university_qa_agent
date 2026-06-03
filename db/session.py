import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Generator

from db.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./university.db")

engine = create_engine(
    DATABASE_URL,
    # Needed for SQLite when used across threads (e.g. FastAPI)
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
    echo=False,  # Set to True to log all SQL statements during dev
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create all tables. Safe to call multiple times (no-op if already exists)."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Return a raw session. Caller is responsible for closing."""
    return SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for safe session lifecycle with automatic rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_schema_context() -> str:
    """
    Introspect the live database and generate a textual schema description
    for injection into the LLM prompt. This makes the agent truly DB-agnostic —
    adding a new table to models.py is automatically reflected in the agent context.
    """
    inspector = inspect(engine)
    lines = []

    for table_name in inspector.get_table_names():
        lines.append(f"TABLE: {table_name}")

        # Columns
        for col in inspector.get_columns(table_name):
            nullable = ", nullable" if col["nullable"] else ""
            lines.append(f"  - {col['name']} ({col['type']}{nullable})")

        # Foreign keys
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            local_col = fk["constrained_columns"][0]
            ref_table = fk["referred_table"]
            ref_col = fk["referred_columns"][0]
            lines.append(f"  - {local_col} → {ref_table}.{ref_col} (FK)")

        lines.append("")  # blank line between tables

    return "\n".join(lines)
