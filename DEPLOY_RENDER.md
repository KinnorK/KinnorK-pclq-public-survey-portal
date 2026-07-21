# Deploying the PCLQ System on Render

## What the Blueprint creates

`render.yaml` provisions a Docker web service and a managed PostgreSQL database in the Singapore region. The database has no public IP allow-list and is connected to the web service through its managed connection string.

## Required secrets

During initial Blueprint creation, Render asks for:

- `FOUNDER_PASSWORD`: minimum 10 characters; use a strong temporary password.
- `ANALYST_PASSWORD`: minimum 10 characters; use a different strong temporary password.

`SECRET_KEY` is generated automatically. Do not replace it with a short value.

## Successful deployment check

Open these paths using the generated service address:

- `/health` returns a JSON response containing `status: ok` and `database: ok`.
- `/survey` displays the public questionnaire.
- `/login` displays the restricted login page.

## Custom domain

A custom domain is optional. The generated service subdomain already uses HTTPS. When a custom domain is activated, add:

`PUBLIC_BASE_URL=https://your-final-domain.example`

in the service environment and redeploy. This ensures downloaded QR codes keep the final address.

## Updating the software

Push updated files to the connected GitHub branch. Render rebuilds the Docker image and redeploys the web service. PostgreSQL data remains in the separate managed database.

## Recovery

Database recovery is a hosting-account operation. Restrict it to the Founder or an authorized institutional administrator. Do not download unencrypted database dumps to shared personal computers.
