"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(email, password);
      if (!data.access_token) {
        throw new Error("No access token returned.");
      }
      localStorage.setItem("access_token", data.access_token);
      router.push("/dashboard");
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Login failed";
      // Show user-friendly auth errors instead of raw API payloads.
      if (raw.includes("invalid_credentials") || raw.toLowerCase().includes("invalid login credentials")) {
        setError("Incorrect email or password. Please try again.");
      } else {
        setError(raw);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="card w-full max-w-md p-6">
        <h1 className="text-3xl font-bold tracking-tight text-slate-950">Login</h1>
        <p className="mt-1 text-sm font-medium text-slate-700">Sign in to your IntelliDocs account.</p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
              placeholder="••••••••"
            />
          </div>

          {error ? <p className="text-sm text-rose-600">{error}</p> : null}

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-sm text-slate-600">
          New user?{" "}
          <Link href="/register" className="font-medium text-slate-900 underline">
            Create an account
          </Link>
        </p>
      </div>
    </main>
  );
}

