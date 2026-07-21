# Optional Local Testing

Cloud deployment is the final operating mode. Local testing is optional.

From the repository root:

```bash
python -m venv .venv
```

Activate the environment, install requirements, and run:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Local addresses:

- `http://127.0.0.1:8000/survey`
- `http://127.0.0.1:8000/login`

These local addresses are not accessible from anywhere on the internet. Use the HTTPS cloud address after deployment.
