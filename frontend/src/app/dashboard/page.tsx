"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { DocumentItem, listDocuments, uploadDocuments } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("access_token");
    if (!stored) {
      router.replace("/login");
      return;
    }
    setToken(stored);
  }, [router]);

  useEffect(() => {
    if (!token) return;
    void refreshDocs(token);
  }, [token]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const deleted = params.get("deleted");
    if (deleted !== "1") return;

    const rawFilename = params.get("filename");
    const filename = rawFilename?.trim() ? rawFilename : "Document";
    setSuccess(`${filename} was deleted successfully.`);
    router.replace("/dashboard");
  }, [router]);

  async function refreshDocs(authToken: string) {
    setLoadingDocs(true);
    setError("");
    try {
      const docs = await listDocuments(authToken);
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoadingDocs(false);
    }
  }

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!token || selectedFiles.length === 0) return;
    setUploading(true);
    setError("");
    try {
      await uploadDocuments(token, selectedFiles);
      setSelectedFiles([]);
      await refreshDocs(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
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
          <h1 className="text-3xl font-bold tracking-tight text-slate-950">IntelliDocs Dashboard</h1>
          <p className="mt-1 text-sm font-medium text-slate-700">
            Upload documents and manage your personal knowledge base.
          </p>
        </div>
        <div className="flex gap-3">
          <Link href="/chat" className="btn-secondary">
            Open Chat
          </Link>
          <button onClick={logout} className="btn-primary">
            Logout
          </button>
        </div>
      </header>

      {success ? (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <p>{success}</p>
          <button
            type="button"
            onClick={() => setSuccess("")}
            className="rounded-md border border-emerald-300 px-2 py-1 text-xs font-medium hover:bg-emerald-100"
          >
            Dismiss
          </button>
        </div>
      ) : null}

      <section className="card p-4">
        <h2 className="text-lg font-medium text-slate-900">Upload documents</h2>
        <form onSubmit={onUpload} className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
          <div className="w-full">
            <label
              htmlFor="upload-files"
              className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-4 text-center transition hover:border-slate-500 hover:bg-slate-100"
            >
              <span className="text-sm font-semibold text-slate-900">Choose PDF/TXT files</span>
              <span className="mt-1 text-xs text-slate-700">
                {selectedFiles.length > 0
                  ? `${selectedFiles.length} file(s) selected`
                  : "Click here to browse files"}
              </span>
            </label>
            <input
              id="upload-files"
              type="file"
              multiple
              accept=".pdf,.txt"
              onChange={(e) => setSelectedFiles(Array.from(e.target.files ?? []))}
              className="hidden"
            />
          </div>
          <button
            type="submit"
            disabled={uploading || selectedFiles.length === 0}
            className="btn-primary"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </form>
      </section>

      <section className="card mt-6 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-medium text-slate-900">My documents</h2>
          <button onClick={() => void refreshDocs(token)} className="btn-secondary">
            Refresh
          </button>
        </div>

        {loadingDocs ? <p className="text-sm text-slate-600">Loading documents...</p> : null}
        {!loadingDocs && documents.length === 0 ? (
          <p className="text-sm text-slate-600">No documents uploaded yet.</p>
        ) : null}

        <div className="space-y-2">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
              <div>
                <p className="text-sm font-medium text-slate-900">{doc.filename}</p>
                <p className="text-xs text-slate-600">
                  status: <span className="font-medium">{doc.status}</span> | id: {doc.id}
                </p>
              </div>
              <div className="flex gap-2">
                <Link
                  href={`/chat?document_id=${encodeURIComponent(doc.id)}`}
                  className="btn-secondary rounded-md px-3 py-1.5 text-xs"
                >
                  Ask
                </Link>
                <Link
                  href={`/documents/${encodeURIComponent(doc.id)}/delete?filename=${encodeURIComponent(doc.filename)}`}
                  className="btn-danger"
                >
                  Delete
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
    </main>
  );
}

