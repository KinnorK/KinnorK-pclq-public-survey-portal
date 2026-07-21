from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SECRET = "change-this-secret-before-deployment"
DEFAULT_FOUNDER_PASSWORD = "change-me-now"
DEFAULT_ANALYST_PASSWORD = "analysis123"


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_base_url(value: str | None) -> str:
    """Return a safe absolute base URL and repair common typing mistakes."""
    raw = (value or "").strip().strip('"').strip("'")
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.startswith(("http://", "https://")):
        return raw.rstrip("/")
    repairs = (
        ("hhttps://", "https://"),
        ("hhttp://", "http://"),
        ("https//", "https://"),
        ("http//", "http://"),
        ("https:/", "https://"),
        ("http:/", "http://"),
    )
    for bad, good in repairs:
        if lowered.startswith(bad):
            raw = good + raw[len(bad):]
            break
    if not raw.lower().startswith(("http://", "https://")):
        raw = "http://" + raw.lstrip("/")
    return raw.rstrip("/")


def normalize_database_url(value: str | None) -> str:
    """Normalize cloud PostgreSQL URLs for SQLAlchemy + psycopg 3."""
    raw = (value or "").strip()
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://"):]
    return raw


def _cloud_base_url() -> str:
    explicit = normalize_base_url(os.getenv("PUBLIC_BASE_URL"))
    if explicit:
        return explicit
    render_host = (os.getenv("RENDER_EXTERNAL_HOSTNAME") or "").strip()
    if render_host:
        return f"https://{render_host.strip('/')}"
    railway_host = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway_host:
        return f"https://{railway_host.strip('/')}"
    return ""


def _csv(name: str) -> tuple[str, ...]:
    raw = (os.getenv(name) or "").strip()
    return tuple(x.strip() for x in raw.split(",") if x.strip())


APP_ENV = (os.getenv("APP_ENV") or "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "PCLQ Public Survey and Research Portal")
    environment: str = APP_ENV
    database_url: str = normalize_database_url(
        os.getenv(
            "DATABASE_URL",
            f"sqlite:///{(DATA_DIR / 'pclq_public_portal.sqlite3').as_posix()}",
        )
    )
    secret_key: str = os.getenv("SECRET_KEY", DEFAULT_SECRET)
    public_base_url: str = _cloud_base_url()
    timezone: str = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    session_https_only: bool = _bool("SESSION_HTTPS_ONLY", IS_PRODUCTION)
    founder_username: str = os.getenv("FOUNDER_USERNAME", "admin")
    founder_password: str = os.getenv("FOUNDER_PASSWORD", DEFAULT_FOUNDER_PASSWORD)
    analyst_username: str = os.getenv("ANALYST_USERNAME", "analyst")
    analyst_password: str = os.getenv("ANALYST_PASSWORD", DEFAULT_ANALYST_PASSWORD)
    minimum_core_items: int = int(os.getenv("MINIMUM_CORE_ITEMS", "16"))
    prorate_likert_if_one_missing: bool = _bool("PRORATE_LIKERT_IF_ONE_MISSING", False)
    trusted_hosts: tuple[str, ...] = _csv("TRUSTED_HOSTS")
    db_startup_attempts: int = int(os.getenv("DB_STARTUP_ATTEMPTS", "30"))
    db_startup_delay_seconds: float = float(os.getenv("DB_STARTUP_DELAY_SECONDS", "2"))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate_for_startup(self) -> None:
        problems: list[str] = []
        if not self.database_url:
            problems.append("DATABASE_URL is missing")
        if self.is_production:
            if self.secret_key == DEFAULT_SECRET or len(self.secret_key) < 32:
                problems.append("SECRET_KEY must be a unique value of at least 32 characters")
            if self.founder_password == DEFAULT_FOUNDER_PASSWORD:
                problems.append("FOUNDER_PASSWORD must be changed from the demonstration password")
            if self.analyst_password == DEFAULT_ANALYST_PASSWORD:
                problems.append("ANALYST_PASSWORD must be changed from the demonstration password")
            if self.founder_password == self.analyst_password:
                problems.append("Founder and Analyzer passwords must be different")
            if not self.session_https_only:
                problems.append("SESSION_HTTPS_ONLY must be true in production")
        if problems:
            raise RuntimeError("Unsafe or incomplete configuration: " + "; ".join(problems))


settings = Settings()
