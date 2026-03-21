# Debugging the backend locally (wrong or weak answers)

Use this when **chat answers feel wrong**, **“I don’t know”** appears often, or answers look like **raw excerpts** instead of a normal reply.

## 1. Run the API from `backend/`

```powershell
cd backend
.\venv\Scripts\Activate.ps1   # or your venv
pip install -r requirements.txt
# Ensure backend/.env is filled (same Supabase + DB as your data, or a test project)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001 --log-level info
```

Watch the terminal on each question: you should see lines like:

- `rag_query: retrieved=N top_sim=0.xxxx ...`
- `rag_query: Gemini failed, using extractive fallback — ...` (means the model API failed; answer is **not** from Gemini)
- `rag_query: no chunks retrieved ...` (retrieval failed before any LLM call)

## 2. Turn on `RAG_DEBUG` (response JSON)

In `backend/.env`:

```env
RAG_DEBUG=1
```

Restart Uvicorn. `POST /query` responses then include a **`debug`** object, for example:

| Field | What it tells you |
|--------|-------------------|
| `chunks_retrieved` | `0` → no vectors matched (wrong doc, not `ready`, or empty PDF text). |
| `top_similarities` | Cosine similarity of top chunks. Very low (e.g. &lt; 0.25) often means **bad retrieval** (embedding mismatch or irrelevant chunks). |
| `answer_source` | `gemini` vs `extractive` — if `extractive`, you’re not getting a Gemini-written answer. |
| `gemini_error` | Exact error when Gemini failed (key, model name, quota, API message). |
| `top_chunk_preview` | First ~400 chars of the best-matching chunk — check if it’s the **right part of the doc**. |
| `embeddings_model` | Must match what was used at **ingest** time (`EMBEDDINGS_LOCAL_MODEL`). |

Unset `RAG_DEBUG` in production if you don’t want extra fields on responses.

## 3. Call `/query` manually (curl)

1. Login: `POST /auth/login` → copy `access_token`.
2. Query:

```bash
curl -s -X POST "http://127.0.0.1:8001/query" ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"YOUR QUESTION\",\"document_id\":\"OPTIONAL-UUID\",\"top_k\":6}"
```

Inspect **`sources[].similarity`** and snippets even without `RAG_DEBUG`.

## 4. Common causes of “incorrect” behavior

1. **Silent Gemini failure** (fixed in recent versions): check logs for `Gemini failed` or `debug.gemini_error`. Wrong `GEMINI_MODEL`, invalid key, or network issues → **extractive** answers that can look odd.
2. **No / weak retrieval**: `chunks_retrieved: 0` or very low `top_similarities`. Causes: document still processing, PDF with little text in the **first 12 pages** (ingestion limit), wrong `document_id`, or chunks created with a **different embedding model** than query (re-upload after changing `EMBEDDINGS_LOCAL_MODEL`).
3. **Gemini following strict prompt**: The system prompt says to answer only from `CONTEXT` and say **“I don’t know”** if it’s not there — if the **top chunks** don’t contain the answer, behavior is expected.
4. **Frontend pointing at wrong API**: `NEXT_PUBLIC_API_BASE_URL` must match your local port (e.g. `http://127.0.0.1:8001`).

## 5. Quick health check

`GET http://127.0.0.1:8001/health` → `{"status":"ok"}`.

Startup logs should show `LLM=gemini` (if key set) and `embeddings=local`.
