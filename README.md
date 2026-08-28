# Service RAG — Setup Guide

A strict documentation-grounded RAG (Retrieval-Augmented Generation) API with a chat widget frontend. The system only answers questions when it can confidently ground the answer in the indexed documentation — otherwise it refuses rather than guesses.

---

## Project Structure

```
Service-RAG-main/
├── frontend-bot/          ← Chat widget (HTML/CSS/JS)
│   ├── index.html
│   ├── style.css
│   └── script.js
├── data/                  ← Source documentation (.md file)
├── ingestion/              ← Scripts that chunk + embed + index the docs
├── retrieval/              ← Retrieval logic (Hugging Face embeddings)
├── generation/              ← Answer generation logic (Groq LLM)
├── vector_store/            ← Qdrant vector database interface
├── tests/
├── api.py                  ← FastAPI app (all HTTP routes)
├── config.py                ← All settings (env vars, CORS, prefixes)
├── rag_pipeline.py           ← Orchestrates retrieval → generation → verification
├── requirements.txt
└── .env.example              ← Template for required secrets
```

---

## 1. Prerequisites

- **Python 3.10+** installed and added to PATH (`python --version` should work in your terminal)
- A **Hugging Face** account (free) → for embeddings
- A **Groq** account (free) → for answer generation
- A running **Qdrant** instance (local Docker, or Qdrant Cloud free tier)

---

## 2. Install dependencies

From the project root (the folder containing `api.py`):

```bash
python -m pip install -r requirements.txt
python -m pip install sentence-transformers
```

> `sentence-transformers` isn't in `requirements.txt` but is required by the ingestion step — install it separately as shown above.

---

## 3. Set up environment variables

Copy the example env file:

```bash
copy .env.example .env        # Windows
cp .env.example .env           # Mac/Linux
```

Open `.env` and fill in:

```dotenv
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500
```

**Where to get the keys:**
- **HF_TOKEN** → huggingface.co → Settings → Access Tokens → New token (Read access is enough)
- **GROQ_API_KEY** → console.groq.com → API Keys → Create API Key

`ALLOWED_ORIGINS` must include whatever address your frontend runs on. If you use VS Code's **Live Server** extension, that's usually `http://127.0.0.1:5500` — add your actual port if different.

---

## 4. Index the documentation

This step reads the `.md` file in `data/`, chunks it, generates embeddings, and uploads them to Qdrant. Run it once, and again any time the source document changes:

```bash
python -m ingestion.sync
```

You should see `RAG INDEX ACTIVATED` at the end with a chunk count. If it fails, check that Qdrant is running and reachable, and that `HF_TOKEN` is set correctly.

---

## 5. Run the backend

```bash
python -m uvicorn api:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Verify it's working** — open in a browser:
- `http://127.0.0.1:8000/health` → should return `{"status":"ok",...}`
- `http://127.0.0.1:8000/ready` → should return `{"status":"ready","collection":"..."}`
  (If this returns `not_ready`, re-run step 4.)

Keep this terminal open — closing it stops the backend.

---

## 6. Run the frontend

The chat widget lives in `frontend-bot/index.html`. It's a plain HTML/CSS/JS app — no build step needed.

**Easiest way:** install the **Live Server** extension in VS Code, right-click `frontend-bot/index.html` → **"Open with Live Server."** It'll open in your browser, typically at `http://127.0.0.1:5500/frontend-bot/index.html`.

**First-time setup inside the widget:**
1. Click the chat bubble (bottom-right) to open it
2. Click the ⚙️ gear icon in the header
3. Set:
   - **API base URL:** `http://127.0.0.1:8000`
   - **Prefix:** `/api/v1` (must match `API_PREFIX` in `config.py`)
4. These are saved in your browser automatically — you won't need to re-enter them next time.

The status dot under "Chatbot" should turn **green ("Online")** once connected.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Status dot shows "Offline" or HTTP error | Backend isn't running, or your frontend's address isn't in `ALLOWED_ORIGINS` in `.env` |
| Status dot shows "Index not ready" | Run `python -m ingestion.sync` (step 4) |
| Every question gets refused with "couldn't provide a reliable answer" | Check the backend terminal logs right after asking — look for `HF_TOKEN is not set` or Groq-related errors, meaning a key is missing/invalid; if keys are fine, the document may genuinely not cover that topic, or the question needs to be phrased closer to the doc's wording |
| `ModuleNotFoundError` on startup | Re-run step 2 (pip install) |
| `.env` changes don't seem to apply | Restart the backend — env vars are only read on startup, not on `--reload` |

---

## API Reference (for frontend/integration work)

**`POST /api/v1/chat`**
```json
// Request
{ "question": "your question here" }

// Response
{
  "success": true,
  "answer": "...",
  "error": null,
  "request_id": "..."
}
```
`success: false` means the system deliberately declined to answer — this is expected behavior for a strict RAG system, not a bug. Sources, retrieved chunks, and internal scoring are never exposed by the API.

**`GET /health`** — liveness check.
**`GET /ready`** — confirms the vector index is active and populated.
