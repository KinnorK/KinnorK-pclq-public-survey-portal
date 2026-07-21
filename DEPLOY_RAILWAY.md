# Alternative Deployment on Railway

The package includes `railway.toml` and a Dockerfile.

1. Create a Railway project from the private GitHub repository.
2. Add a PostgreSQL service.
3. Link the application service to PostgreSQL and provide `DATABASE_URL`.
4. Set these variables on the application service:
   - `APP_ENV=production`
   - `SECRET_KEY` with at least 32 random characters
   - `SESSION_HTTPS_ONLY=true`
   - `APP_TIMEZONE=Asia/Kolkata`
   - `FOUNDER_USERNAME=admin`
   - `FOUNDER_PASSWORD` with a strong temporary password
   - `ANALYST_USERNAME=analyst`
   - `ANALYST_PASSWORD` with a different strong temporary password
5. Generate a public domain from the application service Networking settings.
6. Set `PUBLIC_BASE_URL` to the generated HTTPS domain and redeploy.
7. Verify `/health`, `/survey`, and `/login`.

Render Blueprint is the primary documented route because it provisions the web service and database together from one infrastructure file.
