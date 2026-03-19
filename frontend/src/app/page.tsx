"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      router.replace("/dashboard");
      return;
    }
    router.replace("/login");
  }, [router]);

  return (
    <main className="min-h-screen flex items-center justify-center">
      <p className="text-slate-700">Redirecting...</p>
    </main>
  );
}
