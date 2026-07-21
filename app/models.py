from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), index=True)  # founder | analyst
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StateSequence(Base):
    __tablename__ = "state_sequences"
    __table_args__ = (UniqueConstraint("state_tag", "year", name="uq_state_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_tag: Mapped[str] = mapped_column(String(2), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    gender_other: Mapped[str | None] = mapped_column(String(120), nullable=True)
    education: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    education_other: Mapped[str | None] = mapped_column(String(120), nullable=True)
    academic_background: Mapped[str] = mapped_column(String(50), index=True)
    state_ut: Mapped[str] = mapped_column(String(100), index=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)

    response_json: Mapped[str] = mapped_column(Text)
    item_scores_json: Mapped[str] = mapped_column(Text)
    missing_items_json: Mapped[str] = mapped_column(Text)
    scoring_version: Mapped[str] = mapped_column(String(30), default="PCLQ-1.0")

    prior_awareness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_b_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symptom_recognition_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    help_seeking_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genetic_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    core_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    core_completed: Mapped[int] = mapped_column(Integer, default=0)
    core_missing: Mapped[int] = mapped_column(Integer, default=20)
    core_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    core_level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    core_warning: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_perception_raw: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    risk_perception_standardized: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_perception_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    screening_intention_raw: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    screening_intention_standardized: Mapped[float | None] = mapped_column(Float, nullable=True)
    screening_intention_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    questionnaire_completion_percentage: Mapped[float] = mapped_column(Float, default=0)

    submitted_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    participant_code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
