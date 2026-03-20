/**
 * Typed fetch helpers for the FastAPI backend.
 * Base URL comes from Vercel env in production; defaults to local uvicorn in dev.
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8001";

export type AuthResponse = {
  access_token?: string;
  token_type?: string;
  requires_email_confirmation?: boolean;
};

export type DocumentItem = {
  id: string;
  filename: string;
  status: string;
};

export type SourceChunk = {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  chunk_index: number;
  snippet: string;
  similarity: number;
};

export type QueryResponse = {
  conversation_id: string;
  answer: string;
  sources: SourceChunk[];
};

/** Parse JSON body, or fall back to plain text (avoids throw on empty/HTML errors). */
async function parseJsonSafe(resp: Response): Promise<unknown> {
  try {
    return await resp.json();
  } catch {
    return await resp.text();
  }
}

function toErrorMessage(payload: unknown): string {
  if (typeof payload === "string") {
    return payload;
  }
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (typeof obj.detail === "string") {
      return obj.detail;
    }
    if (obj.detail) {
      return JSON.stringify(obj.detail);
    }
    return JSON.stringify(obj);
  }
  return "Unexpected error";
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const resp = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(toErrorMessage(data));
  }
  return data as AuthResponse;
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const resp = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(toErrorMessage(data));
  }
  return data as AuthResponse;
}

export async function listDocuments(token: string): Promise<DocumentItem[]> {
  const resp = await fetch(`${API_BASE_URL}/documents`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(toErrorMessage(data));
  }
  return data as DocumentItem[];
}

export async function uploadDocuments(token: string, files: File[]): Promise<DocumentItem[]> {
  const form = new FormData();
  for (const f of files) {
    form.append("files", f);
  }

  const resp = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const data = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(toErrorMessage(data));
  }
  return data as DocumentItem[];
}

export async function deleteDocument(token: string, documentId: string): Promise<void> {
  const resp = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(toErrorMessage(data));
  }
}

export async function queryDocuments(
  token: string,
  payload: { question: string; document_id?: string; top_k?: number; conversation_id?: string }
): Promise<QueryResponse> {
  const resp = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await parseJsonSafe(resp);
  if (!resp.ok) {
    throw new Error(toErrorMessage(data));
  }
  return data as QueryResponse;
}

