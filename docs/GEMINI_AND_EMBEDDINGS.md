# Gemini (answers) + local embeddings

This project uses **only Google Gemini** as a paid API for answer generation. Embeddings run **locally** (sentence-transformers / MiniLM); there is no OpenAI, Anthropic, or Grok integration in this build.

## 1. Local `backend/.env`

Set (no quotes around the key unless your shell requires them). **Each variable must be one line** (`KEY=value`):

```env
GEMINI_API_KEY=<paste from Google AI Studio>
GEMINI_MODEL=gemini-2.0-flash
EMBEDDINGS_PROVIDER=local
EMBEDDINGS_DIM=384
```

If you see a stray line that is only `local`, fix it to `EMBEDDINGS_PROVIDER=local` on a single line.

Restart Uvicorn after saving.

## 2. Install dependencies (local)

Local embeddings need `sentence-transformers` (in `requirements.txt`):

```bash
cd backend
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

First run may download the MiniLM model (~90MB).

## 3. Railway (production)

In the backend service → **Variables**, add or update:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` = `gemini-2.0-flash` (or another supported model name)
- `EMBEDDINGS_PROVIDER` = `local` (required; remove any `openai` value)
- `EMBEDDINGS_DIM` = `384`

Remove unused vars from older setups: `LLM_PROVIDER`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROK_API_KEY` (they are ignored if present, but **`EMBEDDINGS_PROVIDER=openai` will fail startup** — must be `local`).

Then **Redeploy**. The repo pins **CPU-only PyTorch** (via PyTorch’s CPU wheel index) so Railway does not download multi‑GB CUDA packages — builds should finish within the timeout.

If a deploy still times out, check build logs: you should **not** see large `nvidia-cuda-*` / `nvidia-cudnn-*` downloads.

## 4. Re-upload documents (important)

If you previously ingested with another embedding backend and now use **`local`** MiniLM vectors, old chunk vectors may be in a **different embedding space**. Search quality will be wrong until you:

- Delete old documents in the app (or clear `chunks` for those docs in SQL), then **upload again**, **or**
- Keep using the same embedding provider as when the file was first ingested.

## 5. Verify

1. Server logs on startup should show: `LLM=gemini model=...` and `embeddings=local`.
2. `GET http://<backend>/health` → `{"status":"ok"}`.
3. Upload a test PDF → Chat → answer should come from Gemini (or extractive fallback if the key is missing / API errors).

## Model names

If `gemini-2.0-flash` errors, try in `GEMINI_MODEL`:

- `gemini-1.5-flash`
- `gemini-1.5-pro`

Use names supported by [Google AI Studio](https://aistudio.google.com/) for your key.
