from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from .questionnaire import (
    B_SCORED_ITEMS,
    C1_ITEMS,
    CORE_ITEMS,
    D_ITEMS,
    E_ITEMS,
    F_ITEMS,
    OBJECTIVE_KEY,
    REQUIRED_RESPONSE_ITEMS,
)


@dataclass
class ScoreResult:
    scoring_version: str = "PCLQ-1.0"
    prior_awareness_score: int | None = None
    section_b_score: int | None = None
    section_b_completed: int = 0
    symptom_recognition_score: int | None = None
    symptom_recognition_completed: int = 0
    help_seeking_score: int | None = None
    genetic_risk_score: int | None = None
    genetic_risk_completed: int = 0
    core_score: int | None = None
    core_completed: int = 0
    core_missing: int = 20
    core_percentage: float | None = None
    core_level: str | None = None
    core_warning: str | None = None
    risk_perception_raw: float | None = None
    risk_perception_completed: int = 0
    risk_perception_standardized: float | None = None
    risk_perception_level: str | None = None
    risk_perception_prorated: bool = False
    screening_intention_raw: float | None = None
    screening_intention_completed: int = 0
    screening_intention_standardized: float | None = None
    screening_intention_level: str | None = None
    screening_intention_prorated: bool = False
    questionnaire_completed_items: int = 0
    questionnaire_completion_percentage: float = 0.0
    item_scores: dict[str, int | None] = field(default_factory=dict)
    missing_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        cleaned = value.strip().replace("'", "’")
        if cleaned.casefold() in {"", "none", "null", "missing", "n/a", "na"}:
            return None
        if cleaned.casefold() in {"don't know", "don’t know"}:
            return "Don’t know"
        return cleaned
    return value


def _objective_subscore(responses: Mapping[str, Any], items: Iterable[str]):
    total = 0
    completed = 0
    details: dict[str, int | None] = {}
    for item in items:
        value = normalize(responses.get(item))
        if value is None:
            details[item] = None
            continue
        completed += 1
        point = int(str(value) == OBJECTIVE_KEY[item])
        details[item] = point
        total += point
    return (total if completed else None), completed, details


def _likert_score(responses: Mapping[str, Any], items: Iterable[str], prorate: bool):
    values: list[float] = []
    for item in items:
        value = normalize(responses.get(item))
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 5:
            values.append(number)
    if len(values) == 5:
        return float(sum(values)), 5, False
    if len(values) == 4 and prorate:
        return round(sum(values) / 4 * 5, 2), 4, True
    return None, len(values), False


def _core_level(score: int | None) -> str | None:
    if score is None:
        return None
    if score <= 9:
        return "Low"
    if score <= 14:
        return "Moderate"
    return "High"


def _likert_level(raw: float | None) -> str | None:
    if raw is None:
        return None
    if raw <= 11:
        return "Low"
    if raw <= 18:
        return "Moderate"
    return "High"


def score_questionnaire(
    responses: Mapping[str, Any],
    *,
    minimum_core_items: int = 16,
    prorate_likert_if_one_missing: bool = False,
) -> ScoreResult:
    if not 1 <= minimum_core_items <= 20:
        raise ValueError("minimum_core_items must be between 1 and 20")

    b_score, b_completed, b_details = _objective_subscore(responses, B_SCORED_ITEMS)
    c_score, c_completed, c_details = _objective_subscore(responses, C1_ITEMS)
    d_score, d_completed, d_details = _objective_subscore(responses, D_ITEMS)
    item_scores = {**b_details, **c_details, **d_details}
    core_completed = b_completed + c_completed + d_completed
    core_missing = 20 - core_completed
    observed = sum(v or 0 for v in item_scores.values())
    core_score = observed if core_completed >= minimum_core_items else None
    core_percentage = round(core_score / 20 * 100, 2) if core_score is not None else None
    warning = None
    if core_completed < minimum_core_items:
        warning = f"Core score not released: only {core_completed} of 20 objective items were completed."
    elif core_missing:
        warning = f"Core score uses {core_completed} completed items; {core_missing} responses remain missing."

    b1 = normalize(responses.get("B1"))
    c2 = normalize(responses.get("C2"))
    e_raw, e_completed, e_prorated = _likert_score(responses, E_ITEMS, prorate_likert_if_one_missing)
    f_raw, f_completed, f_prorated = _likert_score(responses, F_ITEMS, prorate_likert_if_one_missing)
    e_std = round((e_raw - 5) / 20 * 100, 2) if e_raw is not None else None
    f_std = round((f_raw - 5) / 20 * 100, 2) if f_raw is not None else None

    missing = [item for item in REQUIRED_RESPONSE_ITEMS if normalize(responses.get(item)) is None]
    completed = len(REQUIRED_RESPONSE_ITEMS) - len(missing)
    completion_pct = round(completed / len(REQUIRED_RESPONSE_ITEMS) * 100, 2)

    return ScoreResult(
        prior_awareness_score=None if b1 is None else int(b1 == "Yes"),
        section_b_score=b_score,
        section_b_completed=b_completed,
        symptom_recognition_score=c_score,
        symptom_recognition_completed=c_completed,
        help_seeking_score=None if c2 is None else int(c2 == "Seek medical consultation promptly"),
        genetic_risk_score=d_score,
        genetic_risk_completed=d_completed,
        core_score=core_score,
        core_completed=core_completed,
        core_missing=core_missing,
        core_percentage=core_percentage,
        core_level=_core_level(core_score),
        core_warning=warning,
        risk_perception_raw=e_raw,
        risk_perception_completed=e_completed,
        risk_perception_standardized=e_std,
        risk_perception_level=_likert_level(e_raw),
        risk_perception_prorated=e_prorated,
        screening_intention_raw=f_raw,
        screening_intention_completed=f_completed,
        screening_intention_standardized=f_std,
        screening_intention_level=_likert_level(f_raw),
        screening_intention_prorated=f_prorated,
        questionnaire_completed_items=completed,
        questionnaire_completion_percentage=completion_pct,
        item_scores=item_scores,
        missing_items=missing,
    )
