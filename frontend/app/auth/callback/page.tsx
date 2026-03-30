"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");

    if (token) {
      localStorage.setItem("dhyey_token", token);
      router.push("/dashboard");
    } else {
      router.push("/login");
    }
  }, [searchParams, router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#f8fafc",
      }}
    >
      <Loader2
        style={{ width: "48px", height: "48px", color: "#4f46e5", animation: "spin 1s linear infinite" }}
      />
      <p style={{ marginTop: "16px", color: "#64748b", fontWeight: 500 }}>
        Authenticating...
      </p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#f8fafc" }}>
        <Loader2 style={{ width: "48px", height: "48px", color: "#4f46e5", animation: "spin 1s linear infinite" }} />
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}
