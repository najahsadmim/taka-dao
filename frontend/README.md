# Taka Dao frontend

This folder is a standalone static frontend. In Vercel, create a separate project from this repository and set **Root Directory** to `frontend`.

`config.js` currently points at `https://taka-dao-kkk1.vercel.app`. If your backend project's deployed domain differs, replace that origin and redeploy the frontend. The API URL is public configuration; never put API keys or secrets here.

The frontend requires the separate Flask backend to load and save records. Configure that backend's `FRONTEND_ORIGIN` to the exact deployed frontend origin for browser CORS. No user data is safely persisted until the backend is connected to durable database and file storage.
