
# Bot 42 — Polished Minimal API

## Quick start
```bash
pip install -r requirements.txt
python3 -m uvicorn oracle_api:app --host 0.0.0.0 --port 8000 --reload
```

Open `/docs` for interactive Swagger UI, call **GET /oracle** to generate a prophecy line.
Logs: `prophecy.log`, `reflection_log.json` (auto-created).
