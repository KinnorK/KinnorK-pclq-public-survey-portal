from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from .config import settings
from .models import AuditLog, StateSequence, Submission
from .states import state_tag

def load_application_timezone(name: str):
    """Load the configured timezone, with a Windows-safe IST fallback.

    Some Windows Python installations do not include the IANA timezone
    database. The separate ``tzdata`` package normally supplies it, but the
    fixed UTC+05:30 fallback keeps the PCLQ server operational even when that
    package is temporarily unavailable.
    """
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name in {"Asia/Kolkata", "Asia/Calcutta", "IST"}:
            return timezone(timedelta(hours=5, minutes=30), name="IST")
        raise RuntimeError(
            f"Timezone {name!r} is unavailable. Install the 'tzdata' package "
            "or set APP_TIMEZONE=Asia/Kolkata."
        )


IST = load_application_timezone(settings.timezone)


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def parse_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def submitted_ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(IST)


def generate_participant_code(session: Session, state_ut: str, now_utc: datetime) -> str:
    tag = state_tag(state_ut)
    year = submitted_ist(now_utc).year
    # PostgreSQL and modern SQLite both support this atomic UPSERT + RETURNING.
    sequence = session.execute(
        text(
            """
            INSERT INTO state_sequences (state_tag, year, last_sequence)
            VALUES (:state_tag, :year, 1)
            ON CONFLICT(state_tag, year)
            DO UPDATE SET last_sequence = state_sequences.last_sequence + 1
            RETURNING last_sequence
            """
        ),
        {"state_tag": tag, "year": year},
    ).scalar_one()
    return f"PCLQ-{tag}-{year}-{int(sequence):04d}"


def audit(
    session: Session,
    actor: str,
    action: str,
    participant_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            participant_code=participant_code,
            details_json=json_text(details or {}),
            created_at_utc=datetime.now(timezone.utc).replace(microsecond=0),
        )
    )


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    material = f"{settings.secret_key}|{ip}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _as_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def build_submission_query(params: Any):
    stmt = select(Submission)
    conditions = []

    search = (params.get("search") or "").strip()
    if search:
        conditions.append(Submission.participant_code.ilike(f"%{search}%"))

    states = [s for s in params.getlist("state") if s]
    if states:
        conditions.append(Submission.state_ut.in_(states))

    background = (params.get("background") or "").strip()
    if background:
        conditions.append(Submission.academic_background == background)

    gender = (params.get("gender") or "").strip()
    if gender:
        conditions.append(Submission.gender == gender)

    education = (params.get("education") or "").strip()
    if education:
        conditions.append(Submission.education == education)

    level = (params.get("level") or "").strip()
    if level:
        conditions.append(Submission.core_level == level)

    numeric_filters = [
        ("core_min", Submission.core_score, ">="),
        ("core_max", Submission.core_score, "<="),
        ("risk_min", Submission.risk_perception_raw, ">="),
        ("risk_max", Submission.risk_perception_raw, "<="),
        ("screening_min", Submission.screening_intention_raw, ">="),
        ("screening_max", Submission.screening_intention_raw, "<="),
    ]
    for name, column, op in numeric_filters:
        number = _as_float(params.get(name))
        if number is not None:
            conditions.append(column >= number if op == ">=" else column <= number)

    start_date = params.get("start_date")
    end_date = params.get("end_date")
    start_time = params.get("start_time") or "00:00"
    end_time = params.get("end_time") or "23:59:59"
    if start_date:
        local_start = datetime.combine(date.fromisoformat(start_date), time.fromisoformat(start_time), IST)
        conditions.append(Submission.submitted_at_utc >= local_start.astimezone(timezone.utc))
    if end_date:
        local_end = datetime.combine(date.fromisoformat(end_date), time.fromisoformat(end_time), IST)
        conditions.append(Submission.submitted_at_utc <= local_end.astimezone(timezone.utc))

    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt.order_by(Submission.submitted_at_utc.desc())


def serialize_submission(record: Submission) -> dict[str, Any]:
    local_dt = submitted_ist(record.submitted_at_utc)
    return {
        "id": record.id,
        "participant_code": record.participant_code,
        "age": record.age,
        "gender": record.gender,
        "gender_other": record.gender_other,
        "education": record.education,
        "education_other": record.education_other,
        "academic_background": record.academic_background,
        "state_ut": record.state_ut,
        "consent": record.consent,
        "responses": parse_json(record.response_json, {}),
        "item_scores": parse_json(record.item_scores_json, {}),
        "missing_items": parse_json(record.missing_items_json, []),
        "scoring_version": record.scoring_version,
        "prior_awareness_score": record.prior_awareness_score,
        "section_b_score": record.section_b_score,
        "symptom_recognition_score": record.symptom_recognition_score,
        "help_seeking_score": record.help_seeking_score,
        "genetic_risk_score": record.genetic_risk_score,
        "core_score": record.core_score,
        "core_completed": record.core_completed,
        "core_missing": record.core_missing,
        "core_percentage": record.core_percentage,
        "core_level": record.core_level,
        "core_warning": record.core_warning,
        "risk_perception_raw": record.risk_perception_raw,
        "risk_perception_standardized": record.risk_perception_standardized,
        "risk_perception_level": record.risk_perception_level,
        "screening_intention_raw": record.screening_intention_raw,
        "screening_intention_standardized": record.screening_intention_standardized,
        "screening_intention_level": record.screening_intention_level,
        "questionnaire_completion_percentage": record.questionnaire_completion_percentage,
        "submitted_at_utc": record.submitted_at_utc.isoformat(),
        "submitted_at_ist": local_dt.isoformat(),
        "submitted_date_ist": local_dt.strftime("%d-%m-%Y"),
        "submitted_time_ist": local_dt.strftime("%I:%M:%S %p"),
    }


def export_rows(records: Iterable[Submission]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        data = serialize_submission(record)
        responses = data.pop("responses")
        item_scores = data.pop("item_scores")
        data.pop("missing_items", None)
        data.update(responses)
        data.update({f"score_{k}": v for k, v in item_scores.items()})
        rows.append(data)
    return rows
