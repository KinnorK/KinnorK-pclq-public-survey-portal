# PCLQ Cloud Public Deployment — Start Here

This edition is designed for the final workflow:

1. Anyone opens the public survey from a normal HTTPS link or QR code.
2. The participant does not log in and does not see scores.
3. On submission, the server creates the state-wise PCLQ ID, calculates all scores, and stores the response in PostgreSQL.
4. The Founder and Analyzer log into the private portal.
5. The Founder has analysis plus all administrative controls.
6. The Analyzer has submitted data, filters, scores, reports, and exports only.

## Important

A permanent public address can be created only inside a cloud account owned by you or your institution. This package contains the complete application and deployment configuration, but no third party can safely create the live account, accept charges, choose passwords, or own the research database on your behalf.

## Recommended deployment: Render Blueprint

The included `render.yaml` creates:

- one always-on web service;
- one private managed PostgreSQL database in Singapore;
- HTTPS public access;
- a health check;
- generated application secret;
- prompts for Founder and Analyzer temporary passwords.

The configuration intentionally uses paid production services. Do not use an expiring demonstration database for real research records.

## Deployment steps

1. Create a private GitHub repository named `pclq-survey-portal`.
2. Extract this package.
3. Upload the files inside this folder to the root of that GitHub repository. `render.yaml` and `Dockerfile` must be visible in the repository root.
4. In Render, choose **New → Blueprint**.
5. Connect the private GitHub repository.
6. Render reads `render.yaml` and displays the web service and PostgreSQL database.
7. Enter two different strong temporary passwords when prompted:
   - `FOUNDER_PASSWORD`
   - `ANALYST_PASSWORD`
8. Approve and deploy the Blueprint.
9. Wait until the service health status is **Live**.
10. Open the generated `https://...onrender.com` address.

## Addresses after deployment

- Start page: `https://YOUR-SERVICE.onrender.com/`
- Public survey: `https://YOUR-SERVICE.onrender.com/survey`
- Founder/Analyzer login: `https://YOUR-SERVICE.onrender.com/login`

The computer used for deployment does not need to stay switched on. The cloud service and PostgreSQL database run independently.

## First login

Use the usernames configured in `render.yaml`:

- Founder username: `admin`
- Analyzer username: `analyst`

Use the temporary passwords you entered during deployment. Each account is required to change its password at first login.

## QR code

After Founder login, open **Survey Link and QR Code**. The QR is generated from the live HTTPS address. Download the QR only after the final public domain is confirmed.

## Custom domain

The generated `onrender.com` link already has HTTPS and can be shared. A custom domain is optional. After connecting a custom domain, set `PUBLIC_BASE_URL` in the web service environment to the final address, such as `https://survey.yourorganisation.org`, then redeploy before printing permanent QR materials.

## Data protection checklist

Before real data collection:

- use an institution-owned cloud workspace;
- use strong unique Founder and Analyzer passwords;
- restrict Render workspace membership;
- keep the PostgreSQL database private;
- enable the provider's database backup/recovery features;
- export encrypted research backups on an approved schedule;
- publish the approved participant information/privacy notice;
- obtain required ethics and institutional approvals;
- do not store participant names, phone numbers, or email addresses unless the protocol explicitly requires them.

## Local testing

The Windows launchers are retained for testing. Local addresses such as `127.0.0.1` are not public. Use the cloud URL after deployment.
