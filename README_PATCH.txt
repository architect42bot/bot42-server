
Bot42 Oracle API — PATCH
========================

This patch adds real-time querying to `/oracle`:
  • GET /oracle?q=Your+question
  • POST /oracle  with JSON: {"q":"Your question"}

It keeps /health and /logs/* endpoints and logs answers to logs/prophecy.log.

HOW TO APPLY
------------
1) In Replit, open the `bot42_api_polished` folder.
2) Overwrite its `oracle_api.py` with the file from this ZIP.
   (Drag-and-drop or copy/paste contents.)
3) Ensure your `.replit` points to `bot42_api_polished/oracle_api.py`.
4) Set the Replit Secret `OPENAI_API_KEY` (and optionally `BOT42_MODEL`).
5) Click RUN, then test:
      /oracle?q=Encourage%20me
   or via Swagger at /docs (POST /oracle).

Notes:
  • Default model is gpt-4o-mini; override with env BOT42_MODEL.
  • Answers are appended to logs/prophecy.log.
  • If `pydantic` is present, FastAPI uses it; otherwise a simple fallback schema is used.
