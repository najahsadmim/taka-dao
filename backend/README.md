# Taka Dao backend

This folder contains the standalone Flask API. In Vercel, create a separate project from this repository and set **Root Directory** to `backend`; Vercel detects `app.py` and `requirements.txt`.

Set private environment variables in the backend project, as needed:

- `FLASK_SECRET_KEY`
- `FRONTEND_ORIGIN` — exact deployed frontend origin, such as `https://taka-dao.vercel.app`
- Ollama variables (`AI_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and private `OLLAMA_API_KEY` for Cloud)
- `DOCUMENT_ENCRYPTION_KEY` if document encryption is enabled

Vercel's local function filesystem is temporary. This prototype writes JSON and encrypted uploads locally; do not use it for real student records until those are migrated to durable database and object storage and authentication/authorization is added.
