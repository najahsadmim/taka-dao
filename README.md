# Taka Dao

A local-first prototype for international students to see recorded spending, upcoming obligations and expected funding in one place. The design uses the supplied blue banknote palette and compact finance shortcuts as inspiration, without copying banknote artwork or another provider's branding.

## Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set OLLAMA_API_KEY for Ollama Cloud, or use local Ollama without a key.
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Demo records are synthetic. Use **Reset demo data**? The API reset endpoint `POST /api/reset-demo` restores the sample data. Payments in this local prototype are previews and never move real money.

## Data and capabilities

- Persistent records live in `data/*.json`; the browser does not store application data.
- Writes use a process lock and atomic file replacement. This is suitable for a single-user local prototype, not a multi-user or multi-process production deployment.
- Successful simulated payments create an idempotent payment event and linked expense. Failed payments create an event and notification, but no expense.
- Dashboard totals and daily category ranking are calculated from records. Automatic daily limit estimates subtract open same-currency dues and a reserve from recorded balance, then account for remaining days in the month. Expected receipts are excluded from cash available. This remains an estimate and depends on complete, consistent records.
- Different currencies are preserved. Amounts in currencies other than the selected display currency are not silently converted or summed into its dashboard totals.
- Tax rules, real payment-provider connections, bank imports, credit bureau access, insurance product recommendations, exports and external notifications are not configured. Document uploads are encrypted at rest using a local Fernet key stored under `.instance/`; uploaded bytes are only served through the local app after decryption. Back up the key securely or encrypted uploads cannot be recovered. When document sharing is enabled, scanned PDF pages and document images can be transcribed through a vision-capable Ollama model; page images are sent to the configured Ollama endpoint for OCR.
- The assistant connects through the Ollama Python client. For local Ollama, set `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://127.0.0.1:11434`, and `OLLAMA_MODEL=gemma4`; a local model needs no API key. For Ollama Cloud, use `OLLAMA_BASE_URL=https://ollama.com`, set `OLLAMA_API_KEY` in the private `.env` file, and select the model name. The assistant status appears in the sidebar. Deterministic finance features work without AI.

## Configuration

Copy `.env.example` to `.env`, then put any Cloud API key only in `.env`. Never commit `.env`, share it, or put secrets in JSON data. Ollama Cloud requests send the key to `ollama.com`; local Ollama requests do not need a key.

## Production limitations

There is no authentication or multi-user authorization in this prototype. Encrypted document storage protects files at rest, but profile fields and application JSON are local plaintext. Keep this service on loopback and do not expose it to a network. Add authentication, authorization, CSRF protection, secret management, and durable multi-user storage before production deployment. Browser location permission is used only to keep a local time zone current; coordinates are ignored and never submitted to the server. Browsers may not offer an “always” location permission for websites.

Run backend checks after installing requirements:

```powershell
python -m unittest discover -s tests -v
```
