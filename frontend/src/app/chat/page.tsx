/**
 * RAG chat: pick a document, ask questions, show answer + cited source snippets.
 */
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { DocumentItem, listDocuments, queryDocuments, QueryResponse } from "@/lib/api";

export default function ChatPage() {
  const router = useRouter();

  const [token, setToken] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("access_token");
    if (!stored) {
      router.replace("/login");
      return;
    }
    setToken(stored);
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get("document_id");
    if (fromUrl) {
      setDocumentId(fromUrl);
    }
  }, [router]);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        const docs = await listDocuments(token);
        setDocuments(docs);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load documents");
      }
    })();
  }, [token]);

  useEffect(() => {
    if (!documentId && documents.length > 0) {
      setDocumentId(documents[0].id);
    }
  }, [documents, documentId]);

  const selectedDoc = useMemo(
    () => documents.find((d) => d.id === documentId) || null,
    [documents, documentId]
  );

  async function onAsk(e: FormEvent) {
    e.preventDefault();
    if (!token || !question.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await queryDocuments(token, {
        question: question.trim(),
        document_id: documentId || undefined,
        top_k: 6,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("access_token");
    router.replace("/login");
  }

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">Chat with documents</h1>
          <p className="mt-1 text-sm font-medium text-slate-700">Ask questions and review source citations.</p>
        </div>
        <div className="flex gap-3">
          <Link href="/dashboard" className="btn-secondary">
            Dashboard
          </Link>
          <button onClick={logout} className="btn-primary">
            Logout
          </button>
        </div>
      </header>

      <section className="card p-5">
        <form onSubmit={onAsk} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Document</label>
            <select
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
            >
              {documents.length === 0 ? <option value="">No documents</option> : null}
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={5}
              placeholder="What are the types of probability distributions?"
              className="w-full rounded-lg border-2 border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-slate-600"
            />
            <p className="mt-1 text-xs text-slate-600">Tip: Ask specific questions for better cited answers.</p>
          </div>

          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="btn-primary px-5 py-2.5"
          >
            {loading ? "Generating answer..." : "Ask"}
          </button>
        </form>
      </section>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      {result ? (
        <section className="mt-6 space-y-4">
          <div className="card p-5">
            <h2 className="text-lg font-medium text-slate-900">Answer</h2>
            {selectedDoc ? <p className="mb-2 text-xs text-slate-600">Document: {selectedDoc.filename}</p> : null}
            <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-900">
              {result.answer}
            </p>
          </div>

          <div className="card p-5">
            <h2 className="text-lg font-medium text-slate-900">Sources</h2>
            {result.sources.length === 0 ? <p className="text-sm text-slate-600">No sources returned.</p> : null}
            <div className="space-y-3">
              {result.sources.map((s) => (
                <div key={s.chunk_id} className="rounded-lg border border-slate-300 bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-slate-800">
                    {s.filename} | page {s.page_number} | similarity {s.similarity.toFixed(3)}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-900">{s.snippet}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}

