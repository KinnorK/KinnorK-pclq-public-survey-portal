# Database Structure

The cloud edition uses PostgreSQL.

## users

Founder and Analyzer accounts, password hashes, role, active status, and first-login password-change status.

## state_sequences

Atomic annual counter for each State/UT tag. It creates identifiers in this format:

`PCLQ-[STATE TAG]-[YEAR]-[SEQUENCE]`

## submissions

Participant demographics, questionnaire responses, item-level scores, all domain scores, literacy level, completion information, state, timestamp in UTC, a keyed hash of source IP, and user-agent metadata.

## audit_log

Restricted log of sign-ins, record viewing, report downloads, user administration, and controlled deletions.

The application creates the required tables on first cloud startup. PostgreSQL data is separate from the web container and therefore remains available across web-service redeployments.
