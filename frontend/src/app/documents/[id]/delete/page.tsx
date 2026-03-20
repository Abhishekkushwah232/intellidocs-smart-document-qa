/**
 * Explicit delete confirmation; on success redirects to dashboard with ?deleted=1 for banner.
 */
"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { deleteDocument } from "@/lib/api";

export default function DeleteDocumentPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [token, setToken] = useState("");
  const [documentId, setDocumentId] = useState(params.id ?? "");
  const [filename, setFilename] = useState("this document");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setDocumentId(params.id ?? "");
  }, [params.id]);

  useEffect(() => {
    const stored = localStorage.getItem("access_token");
    if (!stored) {
      router.replace("/login");
      return;
    }
    setToken(stored);

    const search = new URLSearchParams(window.location.search);
    const name = search.get("filename");
    if (name?.trim()) {
      setFilename(name);
    }
  }, [router]);

  const canConfirm = useMemo(() => token && documentId && !loading, [token, documentId, loading]);

  async function onConfirmDelete() {
    if (!token || !documentId) return;
    setLoading(true);
    setError("");
    try {
      await deleteDocument(token, documentId);
      router.replace(`/dashboard?deleted=1&filename=${encodeURIComponent(filename)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <section className="card w-full max-w-lg p-6">
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">Confirm delete</h1>
        <p className="mt-2 text-sm text-slate-700">
          You are about to permanently delete <span className="font-semibold text-slate-900">{filename}</span>.
        </p>
        <p className="mt-1 text-sm text-rose-700">This action cannot be undone.</p>

        {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

        <div className="mt-6 flex gap-3">
          <Link href="/dashboard" className="btn-secondary">
            Cancel
          </Link>
          <button onClick={() => void onConfirmDelete()} disabled={!canConfirm} className="btn-danger rounded-lg px-4 py-2 text-sm">
            {loading ? "Deleting..." : "Yes, delete"}
          </button>
        </div>
      </section>
    </main>
  );
}
