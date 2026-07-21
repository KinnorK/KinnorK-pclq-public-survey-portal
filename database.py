from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base, User
from .security import hash_password

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_kwargs = {
    "future": True,
    "pool_pre_ping": True,
    "connect_args": connect_args,
}
if not settings.database_url.startswith("sqlite"):
    engine_kwargs.update({"pool_recycle": 300, "pool_size": 5, "max_overflow": 10})

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_seed_user(session: Session, *, username: str, password: str, role: str, now: datetime) -> None:
    existing = session.scalar(select(User).where(User.username == username))
    if existing:
        return
    session.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            active=True,
            must_change_password=True,
            created_at=now,
            updated_at=now,
        )
    )


def init_db() -> None:
    """Initialize the database with retry support for managed cloud Postgres."""
    settings.validate_for_startup()
    last_error: Exception | None = None
    for attempt in range(1, settings.db_startup_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            Base.metadata.create_all(engine)
            with session_scope() as session:
                now = utc_now()
                _ensure_seed_user(
                    session,
                    username=settings.founder_username,
                    password=settings.founder_password,
                    role="founder",
                    now=now,
                )
                _ensure_seed_user(
                    session,
                    username=settings.analyst_username,
                    password=settings.analyst_password,
                    role="analyst",
                    now=now,
                )
            return
        except Exception as exc:  # pragma: no cover - exercised in real cloud startup
            last_error = exc
            if attempt >= settings.db_startup_attempts:
                break
            time.sleep(settings.db_startup_delay_seconds)
    raise RuntimeError(
        f"Database did not become ready after {settings.db_startup_attempts} attempts"
    ) from last_error
