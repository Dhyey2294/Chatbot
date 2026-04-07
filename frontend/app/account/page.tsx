"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { User, Lock, ArrowLeft, Mail, Calendar, Check, Save, Loader2 } from "lucide-react";

export default function AccountPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setMounted(true);
    const token = localStorage.getItem("mychatai_token");
    if (!token) {
      router.push("/login");
      return;
    }

    const fetchUser = async () => {
      try {
        const res = await axios.get("http://localhost:8000/auth/me", {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUser(res.data);
      } catch (err) {
        if (axios.isAxiosError(err) && err?.response?.status === 401) {
          localStorage.removeItem("mychatai_token");
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [router]);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters.");
      return;
    }

    setIsSaving(true);
    try {
      const token = localStorage.getItem("mychatai_token");
      await axios.patch("http://localhost:8000/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setPasswordSuccess("Password updated successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || "Failed to update password.");
    } finally {
      setIsSaving(false);
    }
  };

  if (!mounted) return null;

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#f8fafc" }}>
         <Loader2 className="animate-spin text-indigo-500" style={{ width: "32px", height: "32px" }} />
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f8fafc", fontFamily: "sans-serif", padding: "48px 32px" }}>
      <div style={{ maxWidth: "600px", margin: "0 auto" }}>
        
        {/* Header Area */}
        <div style={{ marginBottom: "32px" }}>
          <button
            onClick={() => router.push("/dashboard")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "none",
              border: "none",
              color: "#64748b",
              fontSize: "13px",
              fontWeight: 700,
              cursor: "pointer",
              padding: "0",
              marginBottom: "24px",
              textTransform: "uppercase",
              letterSpacing: "0.1em"
            }}
          >
            <ArrowLeft style={{ width: "16px", height: "16px" }} />
            Back to Dashboard
          </button>
          <h1 style={{ fontSize: "32px", fontWeight: 800, color: "#0f172a", margin: 0, letterSpacing: "-0.03em" }}>Account Settings</h1>
        </div>

        {/* Profile Card */}
        <div style={{ backgroundColor: "white", borderRadius: "16px", padding: "32px", boxShadow: "0 4px 20px rgba(0,0,0,0.03)", border: "1px solid #e2e8f0", marginBottom: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "24px", paddingBottom: "24px", borderBottom: "1px solid #f1f5f9" }}>
             <div style={{ width: "64px", height: "64px", borderRadius: "50%", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontSize: "24px", fontWeight: "bold" }}>
                {user?.name ? user.name.charAt(0).toUpperCase() : <User />}
             </div>
             <div>
                <h2 style={{ fontSize: "20px", fontWeight: 800, color: "#0f172a", margin: 0 }}>{user?.name}</h2>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", backgroundColor: "#f0fdf4", color: "#16a34a", padding: "4px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 800, letterSpacing: "0.05em", marginTop: "6px" }}>
                  <Check style={{ width: "12px", height: "12px" }} /> ACTIVE ACCOUNT
                </span>
             </div>
          </div>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
             <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <div style={{ width: "40px", height: "40px", borderRadius: "10px", backgroundColor: "#f8fafc", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
                   <Mail style={{ width: "20px", height: "20px" }} />
                </div>
                <div>
                   <p style={{ margin: 0, fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.1em" }}>Email Address</p>
                   <p style={{ margin: "2px 0 0", fontSize: "14px", fontWeight: 600, color: "#334155" }}>{user?.email}</p>
                </div>
             </div>
             <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <div style={{ width: "40px", height: "40px", borderRadius: "10px", backgroundColor: "#f8fafc", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
                   <Calendar style={{ width: "20px", height: "20px" }} />
                </div>
                <div>
                   <p style={{ margin: 0, fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.1em" }}>Member Since</p>
                   <p style={{ margin: "2px 0 0", fontSize: "14px", fontWeight: 600, color: "#334155" }}>
                     {user?.created_at ? new Date(user.created_at).toLocaleString("en-US", { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone, month: "short", day: "numeric", year: "numeric" }) : "Recently"}
                   </p>
                </div>
             </div>
          </div>
        </div>

        {/* Password Reset Card */}
        {user?.hashed_password && (
          <div style={{ backgroundColor: "white", borderRadius: "16px", padding: "32px", boxShadow: "0 4px 20px rgba(0,0,0,0.03)", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "24px" }}>
              <Lock style={{ width: "20px", height: "20px", color: "#0f172a" }} />
              <h2 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a", margin: 0 }}>Change Password</h2>
            </div>

            <form onSubmit={handleChangePassword} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {(passwordError || passwordSuccess) && (
                <div style={{ padding: "12px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: 600, backgroundColor: passwordSuccess ? "#f0fdf4" : "#fef2f2", color: passwordSuccess ? "#16a34a" : "#ef4444", border: `1px solid ${passwordSuccess ? "#bbf7d0" : "#fecaca"}` }}>
                  {passwordError || passwordSuccess}
                </div>
              )}

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#64748b", marginBottom: "6px" }}>Current Password</label>
                <input 
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", border: "1.5px solid #e2e8f0", fontSize: "14px", outline: "none", boxSizing: "border-box" }}
                  required
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#64748b", marginBottom: "6px" }}>New Password</label>
                <input 
                  type="password" 
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", border: "1.5px solid #e2e8f0", fontSize: "14px", outline: "none", boxSizing: "border-box" }}
                  required
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "#64748b", marginBottom: "6px" }}>Confirm New Password</label>
                <input 
                  type="password" 
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "10px", border: "1.5px solid #e2e8f0", fontSize: "14px", outline: "none", boxSizing: "border-box" }}
                  required
                />
              </div>

              <div style={{ marginTop: "8px", display: "flex", justifyContent: "flex-end" }}>
                 <button
                   type="submit"
                   disabled={isSaving}
                   style={{
                     display: "flex",
                     alignItems: "center",
                     gap: "8px",
                     padding: "10px 24px",
                     backgroundColor: "#0f172a",
                     color: "white",
                     border: "none",
                     borderRadius: "10px",
                     fontSize: "13px",
                     fontWeight: 700,
                     cursor: isSaving ? "not-allowed" : "pointer",
                     opacity: isSaving ? 0.7 : 1,
                     transition: "background-color 0.2s"
                   }}
                 >
                   {isSaving ? <Loader2 className="animate-spin" style={{ width: "16px", height: "16px" }} /> : <Save style={{ width: "16px", height: "16px" }} />}
                   Update Password
                 </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
