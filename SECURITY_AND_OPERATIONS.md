# Security and Operations

- Public participants never receive score or database access.
- Founder receives analysis and administration access.
- Analyzer receives data-analysis access only.
- Passwords are stored as salted PBKDF2-SHA256 hashes.
- Forms use signed sessions and CSRF protection.
- Production cookies are HTTPS-only.
- Restricted pages are sent with no-store cache headers.
- PostgreSQL is connected through the hosting provider's private connection.
- The database URL is normalized for psycopg 3 on Render and Railway.
- Application startup refuses known demonstration passwords in production.
- The database health check is exposed at `/health` without exposing records.

Operational responsibilities remain with the institution: workspace access, billing, database recovery, encrypted exports, retention policy, privacy notice, and ethics approval.
