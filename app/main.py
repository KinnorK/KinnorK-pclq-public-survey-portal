from __future__ import annotations

import base64
import csv
import io
import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import qrcode
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import settings
from .database import SessionLocal, init_db, utc_now
from .models import AuditLog, Submission, User
from .questionnaire import (
    BACKGROUND_OPTIONS,
    B2_OPTIONS,
    B3_OPTIONS,
    B_QUESTIONS,
    C2_OPTIONS,
    D_QUESTIONS,
    EDUCATION_OPTIONS,
    E_QUESTIONS,
    F_QUESTIONS,
    GENDER_OPTIONS,
    G_SOURCES,
    ITEM_LABELS,
    REQUIRED_RESPONSE_ITEMS,
    SYMPTOM_QUESTIONS,
    TRUE_FALSE_DK,
    YES_NO,
    YES_NO_DK,
)
from .scoring import score_questionnaire
from .security import current_user, ensure_csrf, hash_password, validate_csrf, verify_password
from .services import (
    audit,
    build_submission_query,
    export_rows,
    generate_participant_code,
    hash_ip,
    json_text,
    parse_json,
    serialize_submission,
    submitted_ist,
)
from .states import STATE_OPTIONS, STATE_TAGS

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > 512_000:
                    return Response("Request too large", status_code=413)
            except ValueError:
                return Response("Invalid Content-Length", status_code=400)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path.startswith(("/portal", "/login", "/change-password")):
            response.headers.setdefault("Cache-Control", "no-store, max-age=0")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url=None, redoc_url=None)
if settings.trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="pclq_session",
    max_age=8 * 60 * 60,
    same_site="lax",
    https_only=settings.session_https_only,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def public_origin(request: Request) -> str:
    if settings.public_base_url:
        return settings.public_base_url
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    scheme = forwarded_proto or request.url.scheme
    host = forwarded_host or request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}".rstrip("/")


def template_context(request: Request, **extra):
    origin = public_origin(request)
    return {
        "request": request,
        "app_name": settings.app_name,
        "user": current_user(request),
        "csrf_token": ensure_csrf(request),
        "survey_url": f"{origin}/survey",
        "portal_url": f"{origin}/login",
        **extra,
    }


def redirect_login() -> RedirectResponse:
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


def portal_user(request: Request, roles: set[str] = {"founder", "analyst"}):
    user = current_user(request)
    if not user:
        return None
    if user.get("role") not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permission")
    return user


def normalize_form_values(form) -> dict[str, str]:
    return {str(k): str(v) for k, v in form.multi_items() if k not in {"csrf_token", "website"}}


def survey_validation(form) -> tuple[dict, dict, list[str]]:
    participant = {
        "age": form.get("age"),
        "gender": form.get("gender"),
        "gender_other": (form.get("gender_other") or "").strip(),
        "education": form.get("education"),
        "education_other": (form.get("education_other") or "").strip(),
        "academic_background": form.get("academic_background"),
        "state_ut": form.get("state_ut"),
        "consent": form.get("consent") == "yes",
    }
    responses: dict[str, object] = {}
    errors: list[str] = []

    try:
        age = int(str(participant["age"]))
        if not 1 <= age <= 120:
            raise ValueError
        participant["age"] = age
    except (TypeError, ValueError):
        errors.append("Enter a valid age from 1 to 120 years.")

    if participant["gender"] not in GENDER_OPTIONS:
        errors.append("Select a gender response.")
    if participant["education"] not in EDUCATION_OPTIONS:
        errors.append("Select the highest educational qualification.")
    if participant["academic_background"] not in BACKGROUND_OPTIONS:
        errors.append("Select the academic background.")
    if participant["state_ut"] not in STATE_TAGS:
        errors.append("Select a valid State or Union Territory.")
    if not participant["consent"]:
        errors.append("Consent is required before the questionnaire can be submitted.")

    allowed = {
        "B1": set(YES_NO),
        "B2": set(B2_OPTIONS),
        "B3": set(B3_OPTIONS),
        "B4": set(TRUE_FALSE_DK),
        "B5": set(TRUE_FALSE_DK),
        "C2": set(C2_OPTIONS),
        **{f"C1_{i}": set(YES_NO_DK) for i in range(1, 13)},
        **{f"D{i}": set(TRUE_FALSE_DK) for i in range(1, 5)},
    }

    for item in REQUIRED_RESPONSE_ITEMS:
        value = form.get(item)
        if item.startswith("E") or item.startswith("F"):
            try:
                numeric = int(str(value))
                if numeric not in {1, 2, 3, 4, 5}:
                    raise ValueError
                responses[item] = numeric
            except (TypeError, ValueError):
                errors.append(f"Complete item {item}.")
        else:
            if value not in allowed.get(item, set()):
                errors.append(f"Complete item {item.replace('_', '.')}.")
            else:
                responses[item] = value

    for item in G_SOURCES:
        responses[item] = form.get(item) == "1"
    responses["G9_text"] = (form.get("G9_text") or "").strip()
    return participant, responses, errors


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root(request: Request):
    return TEMPLATES.TemplateResponse(
        request,
        "start.html",
        template_context(request),
    )


@app.get("/health")
def health():
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok", "service": settings.app_name, "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return Response(
        "User-agent: *\nAllow: /survey\nDisallow: /portal\nDisallow: /login\nDisallow: /change-password\n",
        media_type="text/plain",
    )


@app.get("/survey", response_class=HTMLResponse)
def survey_form(request: Request):
    return TEMPLATES.TemplateResponse(
        request,
        "survey.html",
        template_context(
            request,
            states=STATE_OPTIONS,
            genders=GENDER_OPTIONS,
            education_options=EDUCATION_OPTIONS,
            backgrounds=BACKGROUND_OPTIONS,
            b_questions=B_QUESTIONS,
            b2_options=B2_OPTIONS,
            b3_options=B3_OPTIONS,
            yes_no=YES_NO,
            true_false_dk=TRUE_FALSE_DK,
            yes_no_dk=YES_NO_DK,
            symptom_questions=SYMPTOM_QUESTIONS,
            c2_options=C2_OPTIONS,
            d_questions=D_QUESTIONS,
            e_questions=E_QUESTIONS,
            f_questions=F_QUESTIONS,
            g_sources=G_SOURCES,
            errors=[],
            old={},
        ),
    )


@app.post("/survey", response_class=HTMLResponse)
async def survey_submit(request: Request):
    form = await request.form()
    validate_csrf(request, form.get("csrf_token"))
    if (form.get("website") or "").strip():
        raise HTTPException(status_code=400, detail="Invalid submission")

    participant, responses, errors = survey_validation(form)
    old = normalize_form_values(form)
    if errors:
        return TEMPLATES.TemplateResponse(
            request,
            "survey.html",
            template_context(
                request,
                states=STATE_OPTIONS,
                genders=GENDER_OPTIONS,
                education_options=EDUCATION_OPTIONS,
                backgrounds=BACKGROUND_OPTIONS,
                b_questions=B_QUESTIONS,
                b2_options=B2_OPTIONS,
                b3_options=B3_OPTIONS,
                yes_no=YES_NO,
                true_false_dk=TRUE_FALSE_DK,
                yes_no_dk=YES_NO_DK,
                symptom_questions=SYMPTOM_QUESTIONS,
                c2_options=C2_OPTIONS,
                d_questions=D_QUESTIONS,
                e_questions=E_QUESTIONS,
                f_questions=F_QUESTIONS,
                g_sources=G_SOURCES,
                errors=errors,
                old=old,
            ),
            status_code=422,
        )

    scores = score_questionnaire(
        responses,
        minimum_core_items=settings.minimum_core_items,
        prorate_likert_if_one_missing=settings.prorate_likert_if_one_missing,
    )
    now = utc_now()
    with SessionLocal.begin() as session:
        participant_code = generate_participant_code(session, str(participant["state_ut"]), now)
        record = Submission(
            participant_code=participant_code,
            age=int(participant["age"]),
            gender=str(participant["gender"]),
            gender_other=str(participant["gender_other"] or "") or None,
            education=str(participant["education"]),
            education_other=str(participant["education_other"] or "") or None,
            academic_background=str(participant["academic_background"]),
            state_ut=str(participant["state_ut"]),
            consent=True,
            response_json=json_text(responses),
            item_scores_json=json_text(scores.item_scores),
            missing_items_json=json_text(scores.missing_items),
            scoring_version=scores.scoring_version,
            prior_awareness_score=scores.prior_awareness_score,
            section_b_score=scores.section_b_score,
            symptom_recognition_score=scores.symptom_recognition_score,
            help_seeking_score=scores.help_seeking_score,
            genetic_risk_score=scores.genetic_risk_score,
            core_score=scores.core_score,
            core_completed=scores.core_completed,
            core_missing=scores.core_missing,
            core_percentage=scores.core_percentage,
            core_level=scores.core_level,
            core_warning=scores.core_warning,
            risk_perception_raw=scores.risk_perception_raw,
            risk_perception_standardized=scores.risk_perception_standardized,
            risk_perception_level=scores.risk_perception_level,
            screening_intention_raw=scores.screening_intention_raw,
            screening_intention_standardized=scores.screening_intention_standardized,
            screening_intention_level=scores.screening_intention_level,
            questionnaire_completion_percentage=scores.questionnaire_completion_percentage,
            submitted_at_utc=now,
            source_ip_hash=hash_ip(request.client.host if request.client else None),
            user_agent=(request.headers.get("user-agent") or "")[:1000],
        )
        session.add(record)
        audit(session, "public-survey", "SUBMIT_SURVEY", participant_code, {"state": participant["state_ut"]})

    return RedirectResponse(f"/survey/thanks?code={participant_code}", status_code=303)


@app.get("/survey/thanks", response_class=HTMLResponse)
def survey_thanks(request: Request, code: str = ""):
    return TEMPLATES.TemplateResponse(
        request,
        "thanks.html",
        template_context(request, participant_code=code),
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/portal", status_code=303)
    return TEMPLATES.TemplateResponse(request, "login.html", template_context(request, error=None))


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request):
    form = await request.form()
    validate_csrf(request, form.get("csrf_token"))
    username = (form.get("username") or "").strip()
    password = str(form.get("password") or "")
    with SessionLocal() as session:
        user = session.scalar(select(User).where(func.lower(User.username) == username.lower(), User.active.is_(True)))
        if not user or not verify_password(password, user.password_hash):
            return TEMPLATES.TemplateResponse(
                request,
                "login.html",
                template_context(request, error="Invalid username or password."),
                status_code=401,
            )
        request.session["user"] = {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "must_change_password": user.must_change_password,
        }
        audit(session, user.username, "LOGIN")
        session.commit()
    return RedirectResponse("/change-password" if user.must_change_password else "/portal", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    form = await request.form()
    validate_csrf(request, form.get("csrf_token"))
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    return TEMPLATES.TemplateResponse(request, "change_password.html", template_context(request, error=None))


@app.post("/change-password", response_class=HTMLResponse)
async def change_password_submit(request: Request):
    user = current_user(request)
    if not user:
        return redirect_login()
    form = await request.form()
    validate_csrf(request, form.get("csrf_token"))
    password = str(form.get("password") or "")
    confirm = str(form.get("confirm") or "")
    error = None
    if password != confirm:
        error = "The passwords do not match."
    else:
        try:
            encoded = hash_password(password)
        except ValueError as exc:
            error = str(exc)
    if error:
        return TEMPLATES.TemplateResponse(
            request,
            "change_password.html",
            template_context(request, error=error),
            status_code=422,
        )
    with SessionLocal.begin() as session:
        db_user = session.get(User, int(user["id"]))
        if not db_user:
            request.session.clear()
            return redirect_login()
        db_user.password_hash = encoded
        db_user.must_change_password = False
        db_user.updated_at = utc_now()
        audit(session, db_user.username, "CHANGE_PASSWORD")
    user["must_change_password"] = False
    request.session["user"] = user
    return RedirectResponse("/portal", status_code=303)


@app.get("/portal", response_class=HTMLResponse)
def portal_dashboard(request: Request):
    user = portal_user(request)
    if not user:
        return redirect_login()
    if user.get("must_change_password"):
        return RedirectResponse("/change-password", status_code=303)
    with SessionLocal() as session:
        total = session.scalar(select(func.count(Submission.id))) or 0
        state_count = session.scalar(select(func.count(func.distinct(Submission.state_ut)))) or 0
        mean_core = session.scalar(select(func.avg(Submission.core_score)))
        level_rows = session.execute(
            select(Submission.core_level, func.count(Submission.id)).group_by(Submission.core_level)
        ).all()
        state_rows = session.execute(
            select(Submission.state_ut, func.count(Submission.id))
            .group_by(Submission.state_ut)
            .order_by(func.count(Submission.id).desc())
            .limit(12)
        ).all()
        background_rows = session.execute(
            select(Submission.academic_background, func.count(Submission.id)).group_by(Submission.academic_background)
        ).all()
        recent = session.scalars(select(Submission).order_by(Submission.submitted_at_utc.desc()).limit(10)).all()
    return TEMPLATES.TemplateResponse(
        request,
        "dashboard.html",
        template_context(
            request,
            total=total,
            state_count=state_count,
            mean_core=round(float(mean_core), 2) if mean_core is not None else None,
            level_counts={k or "Not calculated": v for k, v in level_rows},
            state_counts=state_rows,
            background_counts=background_rows,
            recent=[serialize_submission(r) for r in recent],
        ),
    )


@app.get("/portal/records", response_class=HTMLResponse)
def portal_records(request: Request, page: int = 1):
    user = portal_user(request)
    if not user:
        return redirect_login()
    page = max(page, 1)
    page_size = 100
    stmt = build_submission_query(request.query_params)
    with SessionLocal() as session:
        records = session.scalars(stmt.offset((page - 1) * page_size).limit(page_size + 1)).all()
    has_next = len(records) > page_size
    records = records[:page_size]
    return TEMPLATES.TemplateResponse(
        request,
        "records.html",
        template_context(
            request,
            records=[serialize_submission(r) for r in records],
            states=STATE_OPTIONS,
            backgrounds=BACKGROUND_OPTIONS,
            genders=GENDER_OPTIONS,
            education_options=EDUCATION_OPTIONS,
            selected_states=request.query_params.getlist("state"),
            filters=dict(request.query_params),
            page=page,
            has_next=has_next,
            query_without_page=urlencode([(k, v) for k, v in request.query_params.multi_items() if k != "page"]),
        ),
    )


@app.get("/portal/records/{record_id}", response_class=HTMLResponse)
def portal_record_detail(request: Request, record_id: int):
    user = portal_user(request)
    if not user:
        return redirect_login()
    with SessionLocal() as session:
        record = session.get(Submission, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        data = serialize_submission(record)
        audit(session, user["username"], "VIEW_RECORD", record.participant_code)
        session.commit()
    return TEMPLATES.TemplateResponse(
        request,
        "record_detail.html",
        template_context(request, record=data, item_labels=ITEM_LABELS),
    )


def filtered_records(request: Request):
    with SessionLocal() as session:
        return list(session.scalars(build_submission_query(request.query_params)).all())


@app.get("/portal/export.csv")
def export_csv(request: Request):
    user = portal_user(request)
    if not user:
        return redirect_login()
    records = filtered_records(request)
    rows = export_rows(records)
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("participant_code\n")
    filename = f"pclq_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/portal/export.xlsx")
def export_xlsx(request: Request):
    user = portal_user(request)
    if not user:
        return redirect_login()
    rows = export_rows(filtered_records(request))
    wb = Workbook()
    ws = wb.active
    ws.title = "PCLQ Data"
    if rows:
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column in ws.columns:
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 55)
            ws.column_dimensions[column[0].column_letter].width = width
    else:
        ws.append(["participant_code"])
    meta = wb.create_sheet("Export Metadata")
    meta.append(["Generated at UTC", datetime.now(timezone.utc).isoformat()])
    meta.append(["Generated by", user["username"]])
    meta.append(["Record count", len(rows)])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"pclq_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def build_individual_pdf(data: dict) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("PCLQ Individual Research Report", styles["Title"]), Spacer(1, 6)]
    story.append(Paragraph("Restricted to the Founder and Analyzer team. This is not a diagnostic report.", styles["Italic"]))
    story.append(Spacer(1, 10))
    rows = [
        ["PCLQ ID", data["participant_code"]],
        ["State/UT", data["state_ut"]],
        ["Submitted (IST)", f"{data['submitted_date_ist']} {data['submitted_time_ist']}"],
        ["Academic Background", data["academic_background"]],
        ["General Literacy", f"{data['section_b_score']} / 4"],
        ["Symptom Recognition", f"{data['symptom_recognition_score']} / 12"],
        ["Genetic-Risk Literacy", f"{data['genetic_risk_score']} / 4"],
        ["Core Literacy", f"{data['core_score']} / 20 ({data['core_percentage']}%)"],
        ["Literacy Level", data["core_level"]],
        ["Help-Seeking", f"{data['help_seeking_score']} / 1"],
        ["Risk Perception", f"{data['risk_perception_raw']} / 25"],
        ["Screening Intention", f"{data['screening_intention_raw']} / 25"],
    ]
    table = Table(rows, colWidths=[55 * mm, 115 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    doc.build(story)
    return output.getvalue()


@app.get("/portal/records/{record_id}/report.pdf")
def individual_report_pdf(request: Request, record_id: int):
    user = portal_user(request)
    if not user:
        return redirect_login()
    with SessionLocal() as session:
        record = session.get(Submission, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        data = serialize_submission(record)
        audit(session, user["username"], "DOWNLOAD_INDIVIDUAL_REPORT", record.participant_code)
        session.commit()
    pdf = build_individual_pdf(data)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{data["participant_code"]}_report.pdf"'})


@app.get("/portal/qr.png")
def qr_download(request: Request):
    user = portal_user(request, {"founder"})
    if not user:
        return redirect_login()
    survey_url = f"{public_origin(request)}/survey"
    qr = qrcode.QRCode(version=None, box_size=12, border=4)
    qr.add_data(survey_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(
        buffer.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="PCLQ_Public_Survey_QR.png"'},
    )


@app.get("/portal/qr", response_class=HTMLResponse)
def qr_page(request: Request):
    user = portal_user(request, {"founder"})
    if not user:
        return redirect_login()
    survey_url = f"{public_origin(request)}/survey"
    qr = qrcode.QRCode(version=None, box_size=8, border=4)
    qr.add_data(survey_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    qr_data = base64.b64encode(buffer.getvalue()).decode("ascii")
    return TEMPLATES.TemplateResponse(
        request,
        "qr.html",
        template_context(request, qr_data=qr_data, public_survey_url=survey_url),
    )


@app.get("/portal/users", response_class=HTMLResponse)
def users_page(request: Request):
    user = portal_user(request, {"founder"})
    if not user:
        return redirect_login()
    with SessionLocal() as session:
        users = session.scalars(select(User).order_by(User.username)).all()
    return TEMPLATES.TemplateResponse(request, "users.html", template_context(request, users=users, error=None, success=None))


@app.post("/portal/users", response_class=HTMLResponse)
async def users_create(request: Request):
    actor = portal_user(request, {"founder"})
    if not actor:
        return redirect_login()
    form = await request.form()
    validate_csrf(request, form.get("csrf_token"))
    username = (form.get("username") or "").strip()
    password = str(form.get("password") or "")
    role = str(form.get("role") or "")
    error = None
    if role not in {"founder", "analyst"}:
        error = "Select Founder or Analyzer."
    elif not username:
        error = "Username is required."
    else:
        try:
            encoded = hash_password(password)
        except ValueError as exc:
            error = str(exc)
    if not error:
        now = utc_now()
        try:
            with SessionLocal.begin() as session:
                session.add(User(username=username, password_hash=encoded, role=role, active=True, must_change_password=True, created_at=now, updated_at=now))
                audit(session, actor["username"], "CREATE_USER", details={"username": username, "role": role})
        except IntegrityError:
            error = "That username already exists."
    with SessionLocal() as session:
        users = session.scalars(select(User).order_by(User.username)).all()
    return TEMPLATES.TemplateResponse(
        request,
        "users.html",
        template_context(request, users=users, error=error, success=None if error else "User created."),
        status_code=422 if error else 200,
    )


@app.post("/portal/users/{user_id}/toggle")
async def user_toggle(request: Request, user_id: int):
    actor = portal_user(request, {"founder"})
    if not actor:
        return redirect_login()
    form = await request.form()
    validate_csrf(request, form.get("csrf_token"))
    if int(actor["id"]) == user_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    with SessionLocal.begin() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.active = not user.active
        user.updated_at = utc_now()
        audit(session, actor["username"], "TOGGLE_USER", details={"username": user.username, "active": user.active})
    return RedirectResponse("/portal/users", status_code=303)


@app.post("/portal/records/{record_id}/delete")
async def delete_record(request: Request, record_id: int):
    actor = portal_user(request, {"founder"})
    if not actor:
        return redirect_login()
    form = await request.form()
    validate_csrf(request, form.get("csrf_token"))
    confirmation = (form.get("confirmation") or "").strip()
    with SessionLocal.begin() as session:
        record = session.get(Submission, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        if confirmation != record.participant_code:
            raise HTTPException(status_code=400, detail="PCLQ ID confirmation did not match")
        code = record.participant_code
        audit(session, actor["username"], "DELETE_RECORD", code)
        session.delete(record)
    return RedirectResponse("/portal/records", status_code=303)


@app.get("/portal/audit", response_class=HTMLResponse)
def audit_page(request: Request):
    user = portal_user(request, {"founder"})
    if not user:
        return redirect_login()
    with SessionLocal() as session:
        logs = session.scalars(select(AuditLog).order_by(AuditLog.created_at_utc.desc()).limit(500)).all()
    return TEMPLATES.TemplateResponse(request, "audit.html", template_context(request, logs=logs))
