# Taka Dao frontend

This folder is a standalone static frontend. In Vercel, create a separate project from this repository and set **Root Directory** to `frontend`.

Before deploying, set `TAKA_DAO_API_BASE` in `config.js` to the backend's public origin (for example, `https://taka-dao-api.vercel.app`). Then redeploy the frontend. The API URL is public configuration; never put API keys or secrets here.

The frontend requires the separate Flask backend to load and save records. Configure that backend's `FRONTEND_ORIGIN` to the exact deployed frontend origin for browser CORS. No user data is safely persisted until the backend is connected to durable database and file storage.
