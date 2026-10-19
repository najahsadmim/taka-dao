# 💸 Taka Dao
### AI-powered financial management for international students

> **Plan ahead. Understand your spending. Stay ready for what's due.**

Taka Dao is a web-based financial assistant designed to help international students understand their spending, prepare for upcoming obligations, track expected funding, and use uploaded documents to support tax- and insurance-related questions.

**Live demo:** https://taka-dao.onrender.com/  |  **Source code:** https://github.com/najahsadmim/taka-dao

> [!NOTE]
> **Prototype status:** Taka Dao is a demonstration project. Payments are simulated and do not move real money. Tax and insurance assistance is informational and depends on the available documents and AI configuration. Taka Dao is not a bank, insurer, tax authority, or licensed financial adviser.

---

## 🧭 Contents

- [What Taka Dao helps with](#-what-taka-dao-helps-with)
- [Features](#-features)
- [Smart Budget and suggested spending](#-smart-budget-and-suggested-spending)
- [Smart Fund Allocation](#-smart-fund-allocation)
- [Document security, OCR, and AI assistance](#-document-security-ocr-and-ai-assistance)
- [Technology stack](#-technology-stack)
- [Run locally](#-run-locally)
- [Configure the AI assistant](#-configure-the-ai-assistant)
- [Run tests](#-run-tests)
- [Deployment and persistence](#-deployment-and-persistence)
- [Security and limitations](#-security-and-limitations)
- [Project structure](#-project-structure)
- [License](#-license)

## 🌍 What Taka Dao helps with

International students often need to coordinate tuition, rent, everyday expenses, insurance documents, unfamiliar tax requirements, and funding that may arrive at different times. Taka Dao brings recorded transactions, upcoming dues, expected funds, budgets, and document-aware assistance into one application so users can plan ahead rather than relying on memory alone.

## ✨ Features

### 📊 Financial dashboard
- Summarises recorded balance, current-month expenses, upcoming obligations, expected funding, and transaction counts.
- Shows a daily spending total and the highest-spend categories based on successful expense records for the current day.
- Compares spending against the active daily limit, showing remaining allowance or the amount and percentage over the limit.
- Uses the selected display currency for dashboard totals. Amounts in other currencies are not silently converted or added to those totals.

### 🧾 Transactions and simulated payments
- Record expenses, income, refunds, and transfers with descriptions, dates, categories, amounts, currency, and payment method.
- Use simulated payment methods such as a bank card, digital wallet, and bank transfer.
- A successful simulated payment creates a payment event and linked expense record.
- A failed simulated payment is logged as failed and generates a notification, but does not create a successful expense.
- Payment requests use an idempotency key to help prevent duplicate transactions when the same request is repeated.

**No real money moves.** These flows demonstrate application logic; the prototype is not connected to live banks, card networks, or payment providers.

### 📅 Upcoming dues and obligations
Track future obligations such as tuition instalments, rent, insurance premiums, and other planned bills. Records may include an amount, currency, due date, priority, and status. Open same-currency obligations are considered by the automatic daily-limit estimate.

### 💰 Expected funds
Track potential incoming money such as family support, scholarships, or wages. Expected funding is kept separate from the recorded balance. The dashboard may summarise expected, confirmed, or delayed receipts, but expected receipts are **not** counted as cash already received.

### 🗓️ Planning records and budgets
Use budgets, transactions, upcoming dues, expected funds, and allocations together to understand recorded spending and future commitments. Planning quality depends on keeping the entered amounts, currency codes, and dates accurate. External calendar sync and bank feeds are not configured.

### 🧮 Tax assistant
The AI assistant can explain tax-related questions using the context a user supplies and relevant uploaded documents the user explicitly chooses to share. It can help identify terms, dates, and questions that may need confirmation.

The prototype does **not** include an authoritative tax-rule engine, submit tax returns, or make tax payments. Tax obligations vary by jurisdiction and year; verify important conclusions with official sources or a qualified professional.

### 🩺 Insurance assistant
The AI assistant can help explain insurance policy wording and related records, including uploaded policies, medical bills, or relevant documents where available. It can help users identify benefits, limits, exclusions, dates, and questions to confirm with the insurer.

AI-generated explanations are not a guarantee of coverage or claim approval, a medical diagnosis, or a substitute for the insurer's official policy wording.

### 🔔 In-app notifications
The app stores notifications for events such as recorded transactions, successful or failed simulated payments, new records, and allocation activity. These are **in-app notifications**, not external SMS, email, or mobile push messages.

### 💱 Currency handling
Transactions, dues, funds, budgets, and payment records carry a three-letter currency code. This version does not configure an authoritative live exchange-rate service. Do not assume cross-currency amounts are automatically converted or directly comparable.

## 🧠 Smart Budget and suggested spending

Taka Dao supports manual and automatic daily spending limits.

#### Manual daily limit
- The user sets a daily amount in settings.
- Successful expenses recorded for the current day in the selected display currency are compared with that amount.
- If spending remains within the limit, the dashboard shows the remaining amount.
- If spending exceeds the limit, the dashboard shows how much the limit was exceeded and the percentage over.

#### Automatic daily limit
The app estimates a daily amount using:
1. The recorded balance in the selected display currency.
2. Open obligations recorded in that same currency.
3. The minimum reserve set in settings.
4. The number of days remaining in the month.

The estimate subtracts open same-currency dues and the reserve from the recorded balance, then divides the remainder across the days remaining in the month. Expected receipts are not treated as money already received.

**How suggested spending is shown:** the dashboard displays the active manual limit or automatic estimate as the day's spending boundary. It compares the day's recorded expenses with that amount and shows either the remaining allowance or the over-limit amount and percentage. The category ranking is based on actual transactions recorded for today, rather than generic spending averages.

This is a planning estimate, not a guarantee of affordability or personalised professional financial advice. Missing transactions, inaccurate balances, and obligations entered in other currencies can make the result incomplete.

## 🎯 Smart Fund Allocation

The prototype includes priority-based allocation logic for recorded income and open obligations:

1. The user saves a priority list for obligations.
2. When an income transaction is recorded, the app checks the recorded balance against open obligations in the same currency.
3. If a shortfall is detected and the saved priority list matches due names or categories, the application can earmark some of the income against those obligations.
4. Allocation records update the associated due's allocated amount and generate an in-app notification.
5. An allocation can be reassigned to another open obligation in the same currency through the reallocation endpoint.

Allocation is **recorded planning**, not a bank transfer or bill payment. It depends on the priority list matching obligation names or categories. Review allocations and source records rather than assuming that money has been reserved in a real account.

## 🔐 Document security, OCR, and AI assistance

### Encrypted uploads
Users can upload supported documents and label them by category, including insurance policies, medical records and bills, student visas, admission letters, enrollment verification, transcripts, certificates, passport bio pages, profile photos, and other supported academic documents.

- Uploaded file bytes are encrypted at rest with **Fernet authenticated symmetric encryption** from the Python `cryptography` package.
- The app stores encrypted files in a private-document directory and serves content through an application endpoint after decryption.
- Extracted text may be cached in encrypted form to avoid repeating extraction or OCR work.
- Uploads have size limits and are checked against supported file extensions and basic file signatures.
- Document metadata is stored separately from encrypted file contents.
- By default, the encryption key is stored at `.instance/document.key`. Alternatively, configure `DOCUMENT_ENCRYPTION_KEY` as an environment variable.

**Protect the key.** If the encryption key is lost, encrypted files cannot be recovered. Keep keys and sensitive data out of Git. Encryption of uploaded files does not encrypt all JSON records or metadata, and does not replace authentication or authorisation.

### OCR and document retrieval
When the user enables uploaded-document context for a tax or insurance question, Taka Dao selects relevant document categories and attempts to extract text:

- **PDFs:** extract embedded text; pages with little or no extractable text can be rendered for OCR.
- **Images:** use the configured vision-capable Ollama model to transcribe text.
- **Scanned PDFs:** use PyMuPDF to render pages and a vision-capable Ollama model to transcribe the rendered pages.
- **DOCX files:** extract text from the document package.
- **Extracted text:** may be cached in encrypted form.

The resulting text is included in the AI request as supporting context. The assistant is instructed to flag missing information, avoid promising insurance coverage or claim approval, and identify the uploaded filename when discussing a document. OCR and AI can misread dates, amounts, tables, exclusions, and policy wording; verify important details against the original.

### What is sent to the AI provider?
When document context is enabled, relevant extracted text, or page images for OCR, are sent to the configured Ollama endpoint as part of the request. With local Ollama, the request goes to the locally configured service. With Ollama Cloud, the relevant content is sent to the cloud service. Only enable document context when appropriate, and use synthetic files when testing the hosted demo.


### 🗓️ Monthly Planner
The Planner opens a monthly calendar and places open dues, expected incoming funds, and scheduled Autopay items on their relevant dates. Users can navigate the calendar month and select days to review the events shown. It is a visual planning calendar backed by the app's records, not a synchronised Google/Outlook calendar.

### 🔁 Autopay reminders
Autopay lets users choose an obligation, start date, and recurrence (such as monthly or yearly) to create a scheduled item that appears in the Planner. The interface describes this as a reminder and a payment preview. **The prototype does not execute recurring payments automatically and does not connect to a real payment provider.** Review each payment and approve it yourself through the simulated flow.

### 💳 Payment-method previews
The Payment Methods tool offers local previews for provider styles such as bank, Visa/Mastercard, and PayPal. The preview is for interface testing only: it does not connect to those providers or store full account numbers, card numbers, or security codes. The separate simulated-payment flow uses demo payment methods and creates local records only.

### 📈 Credit-score explainer
The Credit Score shortcut provides educational information about credit history and Bangladesh's Credit Information Bureau (CIB), including a clearly labelled fictional 100-point teaching model. It does **not** calculate an actual credit score, access CIB data, use a bank's scoring formula, or predict loan approval.

### 👤 Profile and settings
The profile form can hold details such as name, date of birth, nationality, residence, university, degree, email, phone, and a profile photo. Settings include theme, country and currency preferences, time zone, tax jurisdiction, and other planning preferences. English is the currently available UI language. These are prototype settings, not a secure multi-user account system.

## 🧰 Technology stack

| Component | Technology |
| --- | --- |
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Data persistence | JSON files |
| Document encryption | Fernet via `cryptography` |
| PDF text extraction | `pypdf` |
| PDF page rendering for scanned-document OCR | PyMuPDF |
| AI and OCR client | Ollama Python client |
| Environment configuration | `python-dotenv` |
| WSGI server | Gunicorn |

## 💻 Run locally

### Prerequisites
- Python 3.10 or newer recommended.
- Git, if you want to clone the repository.
- Ollama local installation or an Ollama Cloud account only if you want AI chat and document OCR.

### 1. Clone the repository
```bash
git clone https://github.com/najahsadmim/taka-dao.git
cd taka-dao
```

If you already downloaded the project, open a terminal in the project root: the directory containing `app.py` and `requirements.txt`.

### 2. Create and activate a virtual environment

**Windows PowerShell**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use the environment's Python directly:
```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Set up environment variables

Create a private `.env` file from the template.

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

You can run the application without a configured AI service; deterministic finance features remain available. Never commit `.env` or put private keys in JSON files.

### 5. Start the Flask app
```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Open the site through Flask rather than opening an HTML file directly, so routes, API requests, and static files resolve correctly.

The application initialises missing JSON collections and can seed demo records. Sample records are synthetic. The `POST /api/reset-demo` endpoint resets app collections to the sample state, so do not call it if you need to keep your local changes.

### Troubleshooting
- **`ModuleNotFoundError`:** check that your virtual environment is selected and run `python -m pip install -r requirements.txt`.
- **CSS or JavaScript not loading:** launch the app with `python app.py` and visit the Flask URL, rather than opening `index.html` directly.
- **AI unavailable:** check the assistant status and the Ollama configuration below.
- **Encrypted document will not open:** confirm the app is using the original encryption key and that the encrypted file remains available. Do not replace the key if you need existing uploads.

## 🤖 Configure the AI assistant

Taka Dao uses the Ollama Python client. Choose a local Ollama service or Ollama Cloud.

### Option A: Local Ollama
1. Install and start Ollama on the computer running Taka Dao.
2. Pull a model that is compatible with your Ollama installation. Document image OCR requires a **vision-capable** model.
3. Set the following values in `.env` and ensure the model name matches one available locally:
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4
OLLAMA_API_KEY=
```
4. Restart Taka Dao.

A local model does not require a cloud API key. If the chosen model cannot accept images, OCR of images and scanned PDF pages will not work.

### Option B: Ollama Cloud
Set the cloud endpoint, model, and private API key in `.env`:
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=your-model-name
OLLAMA_API_KEY=your_private_key_here
```
Replace the example model and key with valid values for your account. Keep the key private and restart the app after changing configuration.

## 🧪 Run tests

Install the requirements, then run the backend test suite:
```bash
python -m unittest discover -s tests -v
```

The existing tests cover daily limit calculations, duplicate prevention for repeated successful simulated-payment requests, and ensuring failed payments do not create expense records. Passing these tests is not a security audit and does not prove every financial scenario is correct.

## 🚀 Deployment and data persistence

The root application can be deployed as a Flask web service. For a WSGI host using Gunicorn, the typical start command is:
```bash
gunicorn app:app
```

This assumes the root `app.py` exposes the Flask instance named `app`. The host should install dependencies from `requirements.txt` and receive any required environment variables through its private configuration panel.

### Important: filesystem persistence
The prototype stores application records in JSON files and encrypted uploads on the local filesystem. Some free hosting platforms have ephemeral filesystems, so local changes may disappear after restart or redeployment. The encryption key can also be lost if it is stored on ephemeral disk.

Before relying on long-lived or real records, migrate JSON storage to durable storage, put encrypted uploads in persistent private object storage, and manage encryption keys separately. Treat the hosted version as a demonstration using synthetic data.

## 🛡️ Security and limitations

Taka Dao has document encryption and basic input/file checks, but it is **not production-ready for sensitive financial, tax, or medical information**.

- The prototype currently has no authentication or multi-user authorisation.
- The default Flask secret key is for local development. Set a strong `FLASK_SECRET_KEY` for any hosted test.
- Application JSON records and some document metadata remain plaintext.
- The document-encryption key must be protected separately from encrypted documents.
- When document context is enabled, relevant extracted text or OCR page images are sent to the configured Ollama endpoint.
- Do not store card numbers, CVVs, PINs, passwords, OTPs, or bank login credentials.
- No live bank connection, payment provider, credit bureau, tax filing provider, or insurer integration is configured.
- Tax and insurance answers may be incomplete or incorrect; check official documents and qualified sources.
- Before public use with real data, add authentication, authorisation, CSRF protection, secure secret management, durable storage, clear privacy controls, and security testing.

Use synthetic documents and transactions when experimenting with the hosted demo.

## 🗂️ Project structure

A simplified view of the repository:

```text
taka-dao/
├── app.py                 # Main Flask application and API routes
├── requirements.txt       # Python dependencies
├── .env.example           # Environment-variable template
├── backend/               # Backend notes and alternate backend copy
├── frontend/              # Frontend source and documentation
├── templates/
│   └── index.html         # Flask-rendered application page
├── static/
│   ├── app.js             # Main browser-side interactions
│   ├── enhancements.js    # UI enhancements
│   └── style.css          # Application styles
├── public/                # Additional static frontend files
├── data/                  # JSON demo records and local app data
├── private_documents/     # Encrypted uploaded-document files
├── tests/
│   └── test_app.py        # Flask/backend tests
└── README.md
```

The repository contains additional frontend/backend copies. The local setup described here uses the root-level `app.py`, `templates/`, and `static/` directories.

## 🤝 Contributing

Bug reports and improvement ideas are welcome. When contributing:
1. Create a branch for your changes.
2. Never commit `.env`, API keys, generated encryption keys, private documents, or real personal records.
3. Add or update tests when changing payment or data-handling logic.
4. Document new environment variables and known limitations.

## 📄 License

This project is distributed under the MIT License. See [LICENSE](LICENSE).

---

<p align="center"><strong>Built to make student finances easier to understand, one decision at a time. 🌍</strong></p>