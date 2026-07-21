# PCLQ Cloud Architecture

```text
Participant phone/computer
        |
        | HTTPS: /survey
        v
Cloud web service (FastAPI)
        |
        | validate + score + state-wise ID
        v
Private managed PostgreSQL database
        ^
        |
        | authenticated HTTPS
Founder / Analyzer portal (/login and /portal)
```

## Public layer

- No participant login.
- Mobile-responsive survey.
- CSRF protection and honeypot field.
- One Submit Survey action.
- Confirmation shows only the PCLQ ID.

## Application layer

- FastAPI and server-rendered templates.
- Automatic objective and Likert scoring.
- Atomic State/UT annual identifier sequence.
- Founder and Analyzer role authorization.
- CSV, Excel, and restricted PDF outputs.
- Health endpoint with a database connectivity check.

## Data layer

- Managed PostgreSQL, not SQLite, in cloud production.
- UTC timestamps stored in the database and displayed in IST.
- Responses, item scores, summary scores, and audit events stored separately.
- Database remains separate from the replaceable web-service container.

## Role boundary

- Founder: all analysis plus administration.
- Analyzer: data and analysis only.
- Participant: survey submission only.
