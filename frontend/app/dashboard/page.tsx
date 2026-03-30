"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { Bot, User, LogOut, Loader2, Plus, Edit, Trash, Check, Zap, Settings } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [bots, setBots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("dhyey_token");
    if (!token) {
      router.push("/login");
      return;
    }

    const fetchData = async () => {
      try {
        const userRes = await axios.get("http://localhost:8000/auth/me", {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUser(userRes.data);

        const botsRes = await axios.get("http://localhost:8000/bots/", {
          headers: { Authorization: `Bearer ${token}` }
        });
        setBots(botsRes.data);
      } catch (err: any) {
        if (err.response?.status === 401) {
          localStorage.removeItem("dhyey_token");
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("dhyey_token");
    router.push("/login");
  };

  const handleDeleteBot = async (botId: string) => {
    if (!confirm("Are you sure you want to delete this chatbot? This cannot be undone.")) return;
    try {
      const token = localStorage.getItem("dhyey_token");
      await axios.delete(`http://localhost:8000/bots/${botId}`, {
         headers: { Authorization: `Bearer ${token}` }
      });
      await axios.delete(`http://localhost:8000/train/${botId}`, {
         headers: { Authorization: `Bearer ${token}` }
      }); // Also delete qdrant data if any
      setBots(bots.filter(b => b.id !== botId));
    } catch (err) {
      console.error("Failed to delete bot", err);
      alert("Failed to delete chatbot.");
    }
  };

  if (loading) {
     return (
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%)" }}>
           <Loader2 style={{ width: "48px", height: "48px", color: "#6366f1", animation: "spin 1s linear infinite" }} />
        </div>
     );
  }

  // Stats calculation
  const totalBots = bots.length;
  const trainedBots = bots.length; // Assuming all are trained
  const currentMonth = new Date().getMonth();
  const currentYear = new Date().getFullYear();
  const createdThisMonth = bots.filter(b => {
      const d = new Date(b.created_at);
      return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
  }).length;

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%)", fontFamily: "sans-serif" }}>
      {/* Navbar */}
      <header
        style={{
          height: "64px",
          backgroundColor: "#ffffff",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 32px",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
          <div style={{ width: "36px", height: "36px", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 2px 4px rgba(99, 102, 241, 0.2)" }}>
            <Bot style={{ color: "white", width: "20px", height: "20px" }} />
          </div>
          <span style={{ fontSize: "24px", fontWeight: 900, color: "#0f172a", textTransform: "uppercase", letterSpacing: "-0.05em" }}>DHYEY</span>
        </Link>

        {user && (
          <div style={{ position: "relative" }} ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "6px 16px 6px 6px",
                borderRadius: "32px",
                transition: "background-color 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f1f5f9")}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", color: "white", fontWeight: "bold", fontSize: "16px" }}>
                 {user.avatar_url ? (
                    <img src={user.avatar_url} alt="Avatar" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                 ) : (
                    user.name ? user.name.charAt(0).toUpperCase() : <User style={{ width: "16px", height: "16px" }} />
                 )}
              </div>
              <span style={{ fontSize: "14px", fontWeight: 600, color: "#334155" }}>{user.name}</span>
            </button>

            {dropdownOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "120%",
                  right: 0,
                  width: "220px",
                  backgroundColor: "#ffffff",
                  borderRadius: "16px",
                  boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
                  border: "1px solid #e2e8f0",
                  padding: "8px",
                  zIndex: 200,
                }}
              >
                <div style={{ padding: "12px 12px", borderBottom: "1px solid #f1f5f9", marginBottom: "8px" }}>
                   <p style={{ margin: 0, fontSize: "13px", color: "#0f172a", fontWeight: 700 }}>{user.name}</p>
                   <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user.email}</p>
                </div>
                
                <button
                  disabled
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "10px 12px",
                    background: "none",
                    border: "none",
                    borderRadius: "8px",
                    color: "#94a3b8",
                    fontSize: "14px",
                    fontWeight: 600,
                    cursor: "not-allowed",
                  }}
                >
                  <Settings style={{ width: "16px", height: "16px" }} />
                  My Account
                </button>

                <button
                  onClick={handleLogout}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "10px 12px",
                    background: "none",
                    border: "none",
                    borderRadius: "8px",
                    color: "#ef4444",
                    fontSize: "14px",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "background-color 0.2s",
                    marginTop: "4px"
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#fef2f2")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <LogOut style={{ width: "16px", height: "16px" }} />
                  Log out
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "48px 64px" }}>
        
        {/* Header Section */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{ width: "6px", height: "40px", background: "linear-gradient(to bottom, #6366f1, #8b5cf6)", borderRadius: "4px" }}></div>
            <div>
              <h1 style={{ fontSize: "32px", fontWeight: 800, color: "#0f172a", margin: "0 0 8px", letterSpacing: "-0.02em" }}>Your Chatbots</h1>
              <p style={{ color: "#64748b", margin: 0, fontSize: "16px", fontWeight: 500 }}>Manage and train your AI assistants.</p>
            </div>
          </div>
          <Link
            href="/build"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#ffffff",
              padding: "14px 28px",
              borderRadius: "12px",
              textDecoration: "none",
              fontWeight: 700,
              fontSize: "15px",
              boxShadow: "0 4px 14px rgba(99, 102, 241, 0.4)",
              transition: "transform 0.2s, box-shadow 0.2s",
            }}
            onMouseEnter={(e) => {
               e.currentTarget.style.transform = "translateY(-2px)";
               e.currentTarget.style.boxShadow = "0 8px 20px rgba(99, 102, 241, 0.5)";
            }}
            onMouseLeave={(e) => {
               e.currentTarget.style.transform = "translateY(0)";
               e.currentTarget.style.boxShadow = "0 4px 14px rgba(99, 102, 241, 0.4)";
            }}
          >
            <Plus style={{ width: "20px", height: "20px" }} />
            Create New Chatbot
          </Link>
        </div>

        {/* Stats Bar */}
        <div style={{ display: "flex", gap: "16px", marginBottom: "48px" }}>
            <div style={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "999px", padding: "8px 20px", fontSize: "13px", fontWeight: 700, color: "#334155", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
               <span style={{ width: "8px", height: "8px", backgroundColor: "#6366f1", borderRadius: "50%" }}></span>
               Total Bots: {totalBots}
            </div>
            <div style={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "999px", padding: "8px 20px", fontSize: "13px", fontWeight: 700, color: "#334155", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
               <span style={{ width: "8px", height: "8px", backgroundColor: "#10b981", borderRadius: "50%" }}></span>
               Trained: {trainedBots}
            </div>
            <div style={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "999px", padding: "8px 20px", fontSize: "13px", fontWeight: 700, color: "#334155", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
               <span style={{ width: "8px", height: "8px", backgroundColor: "#f59e0b", borderRadius: "50%" }}></span>
               Created this month: {createdThisMonth}
            </div>
        </div>

        {bots.length === 0 ? (
          <div style={{
             backgroundColor: "#ffffff",
             border: "1px dashed #cbd5e1",
             borderRadius: "24px",
             padding: "100px 32px",
             textAlign: "center",
             display: "flex",
             flexDirection: "column",
             alignItems: "center",
             boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)"
          }}>
             <div style={{ width: "80px", height: "80px", background: "linear-gradient(135deg, #e0e7ff 0%, #ede9fe 100%)", borderRadius: "24px", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "24px", boxShadow: "0 8px 16px rgba(99, 102, 241, 0.1)" }}>
                <Zap style={{ width: "40px", height: "40px", color: "#6366f1" }} />
             </div>
             <h3 style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", margin: "0 0 16px", letterSpacing: "-0.02em" }}>No chatbots yet</h3>
             <p style={{ color: "#64748b", margin: "0 0 32px", maxWidth: "420px", lineHeight: 1.6, fontSize: "16px" }}>You haven't created any AI assistants yet. Launch your first intelligent chatbot in just a few minutes.</p>
             <Link
                href="/build"
                style={{
                   background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                   color: "#ffffff",
                   padding: "14px 32px",
                   borderRadius: "12px",
                   textDecoration: "none",
                   fontWeight: 700,
                   fontSize: "15px",
                   boxShadow: "0 4px 14px rgba(99, 102, 241, 0.4)",
                   transition: "transform 0.2s, box-shadow 0.2s"
                }}
                onMouseEnter={(e) => {
                   e.currentTarget.style.transform = "translateY(-2px)";
                   e.currentTarget.style.boxShadow = "0 8px 20px rgba(99, 102, 241, 0.5)";
                }}
                onMouseLeave={(e) => {
                   e.currentTarget.style.transform = "translateY(0)";
                   e.currentTarget.style.boxShadow = "0 4px 14px rgba(99, 102, 241, 0.4)";
                }}
             >
                Create your first chatbot
             </Link>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "24px" }}>
            {bots.map((bot) => (
              <div
                key={bot.id}
                style={{
                  backgroundColor: "#ffffff",
                  borderRadius: "16px",
                  padding: "24px",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
                  transition: "box-shadow 0.2s ease, transform 0.2s ease",
                  display: "flex",
                  flexDirection: "column",
                  border: "1px solid rgba(0,0,0,0.04)"
                }}
                onMouseEnter={(e) => {
                   e.currentTarget.style.transform = "translateY(-2px)";
                   e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,0.12)";
                }}
                onMouseLeave={(e) => {
                   e.currentTarget.style.transform = "translateY(0)";
                   e.currentTarget.style.boxShadow = "0 2px 12px rgba(0,0,0,0.08)";
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    <div
                      style={{
                        width: "48px",
                        height: "48px",
                        borderRadius: "50%",
                        background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: "0 4px 8px rgba(99, 102, 241, 0.25)"
                      }}
                    >
                      <span style={{ color: "white", fontSize: "16px", fontWeight: 800 }}>AI</span>
                    </div>
                    <div>
                      <h3 style={{ margin: "0 0 6px", fontSize: "18px", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.01em" }}>{bot.name || "My Bot"}</h3>
                      <div style={{ display: "inline-flex", alignItems: "center", gap: "4px", backgroundColor: "#dcfce7", color: "#16a34a", padding: "2px 10px", borderRadius: "20px", fontSize: "11px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        <Check style={{ width: "12px", height: "12px" }} strokeWidth={3} />
                        Trained
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ marginBottom: "24px", flex: 1 }}>
                   <p style={{ margin: 0, fontSize: "14px", color: "#64748b", fontStyle: "italic", lineHeight: 1.6, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                      "{bot.greeting || "Hi there! How can I help you today?"}"
                   </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px solid #f1f5f9", paddingTop: "20px" }}>
                  <span style={{ fontSize: "13px", color: "#94a3b8", fontWeight: 600 }}>
                    {new Date(bot.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </span>
                  <div style={{ display: "flex", gap: "12px" }}>
                    <button
                      onClick={() => router.push(`/build?bot_id=${bot.id}`)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "8px 16px",
                        backgroundColor: "transparent",
                        color: "#6366f1",
                        border: "1px solid #c7d2fe",
                        borderRadius: "8px",
                        fontSize: "13px",
                        fontWeight: 700,
                        cursor: "pointer",
                        transition: "background-color 0.2s, color 0.2s"
                      }}
                      onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = "#eef2ff";
                      }}
                      onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = "transparent";
                      }}
                    >
                      <Edit style={{ width: "14px", height: "14px" }} />
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteBot(bot.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: "36px",
                        height: "36px",
                        backgroundColor: "transparent",
                        color: "#ef4444",
                        border: "1px solid #fca5a5",
                        borderRadius: "8px",
                        cursor: "pointer",
                        transition: "background-color 0.2s, color 0.2s"
                      }}
                      onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = "#ef4444";
                          e.currentTarget.style.color = "#ffffff";
                      }}
                      onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = "transparent";
                          e.currentTarget.style.color = "#ef4444";
                      }}
                      title="Delete Chatbot"
                    >
                      <Trash style={{ width: "16px", height: "16px" }} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
