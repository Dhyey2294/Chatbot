"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Link2, Plus, Check, Copy, ChevronRight, ChevronLeft, Loader2, Bot, Sparkles, Layout, ArrowRight, Zap, User, MessageSquare, Palette, X, ChevronDown, ChevronUp, RotateCcw, Trash, FileText, Settings, LogOut } from "lucide-react";
import AddKnowledgeModal from "@/components/AddKnowledgeModal";
import LiveChatPreview from "@/components/LiveChatPreview";


const PLATFORMS = [
  {
    name: "HTML",
    icon: "🌐",
    steps: [
      "Copy the code snippet above.",
      "Open your HTML file in a code editor.",
      "Find the closing </body> tag.",
      "Paste the script just before it.",
      "Save the file.",
      "Done — your chatbot will appear on the page!",
    ],
  },
  {
    name: "WordPress",
    icon: "🔵",
    steps: [
      "Copy the code snippet above.",
      "Go to Appearance → Theme Editor in your dashboard.",
      "Open the footer.php file.",
      "Paste the script before the closing </body> tag.",
      "Click Save File.",
      "Done — your chatbot is now live!",
    ],
  },
  {
    name: "Shopify",
    icon: "🛒",
    steps: [
      "Copy the code snippet above.",
      "Go to Online Store → Themes in your Shopify admin.",
      "Click Edit Code on your active theme.",
      "Open the theme.liquid file.",
      "Paste the script before the closing </body> tag.",
      "Save — your chatbot is ready!",
    ],
  },
  {
    name: "Wix",
    icon: "⚡",
    steps: [
      "Copy the code snippet above.",
      "Open your Wix Dashboard.",
      "Go to Settings → Custom Code.",
      "Click Add Custom Code.",
      "Paste the script and set placement to Body.",
      "Save — your chatbot will appear on your site!",
    ],
  },
  {
    name: "Squarespace",
    icon: "⬛",
    steps: [
      "Copy the code snippet above.",
      "Go to Pages and select your page.",
      "Open Page Settings → Advanced.",
      "Find Code Injection and paste in the Footer field.",
      "Click Save.",
      "Done — chatbot is live on Squarespace!",
    ],
  },
  {
    name: "Webflow",
    icon: "🌊",
    steps: [
      "Copy the code snippet above.",
      "Open your Webflow Project Settings.",
      "Go to Custom Code → Footer Code.",
      "Paste the script in the footer code box.",
      "Click Save and then Publish.",
      "Done — your chatbot is now live!",
    ],
  },
  {
    name: "Joomla",
    icon: "🟠",
    steps: [
      "Copy the code snippet above.",
      "Go to Extensions → Templates in Joomla admin.",
      "Click Edit HTML on your active template.",
      "Find the closing </body> tag.",
      "Paste the script just before it.",
      "Save — your chatbot is ready!",
    ],
  },
  {
    name: "Drupal",
    icon: "💧",
    steps: [
      "Copy the code snippet above.",
      "Go to Appearance → Theme Settings.",
      "Find the custom scripts or footer code section.",
      "Paste the script there.",
      "Click Save Configuration.",
      "Done — chatbot is live on Drupal!",
    ],
  },
];

function DeployStep({
  botId,
  copied,
  copyCode,
}: {
  botId: string;
  copied: boolean;
  copyCode: () => void;
}) {
  const [activePlatform, setActivePlatform] = useState<(typeof PLATFORMS)[0] | null>(null);
  const scriptTag = `<script src="http://localhost:3000/widget.js" data-bot-id="${botId || "BOT_ID_HERE"}"></script>`;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%", gap: "48px" }}>

      {/* ── Existing badge + heading (untouched) ── */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "20px", textAlign: "center" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "10px",
            padding: "8px 20px",
            borderRadius: "9999px",
            backgroundColor: "#f0fdf4",
            border: "1px solid #d1fae5",
            color: "#065f46",
            fontSize: "10px",
            fontWeight: 900,
            textTransform: "uppercase",
            letterSpacing: "0.2em",
            boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          }}
        >
          🚀 LAUNCH PHASE
        </div>
        <h2
          style={{
            fontSize: "clamp(40px, 6vw, 64px)",
            fontWeight: 900,
            letterSpacing: "-0.04em",
            color: "#0f172a",
            lineHeight: 1,
            margin: 0,
          }}
        >
          Ready to deploy! 🎉
        </h2>

        {/* ── New heading + subtitle ── */}
        <h3 style={{ fontSize: "22px", fontWeight: 700, color: "#1e293b", margin: "8px 0 0" }}>
          Your Chatbot is Live-Ready
        </h3>
        <p style={{ fontSize: "15px", color: "#64748b", fontWeight: 500, maxWidth: "520px", lineHeight: 1.6, margin: 0 }}>
          Drop this snippet anywhere on your site — your AI assistant will appear instantly.
        </p>
      </div>

      {/* ── Embed code row ── */}
      <div
        style={{
          width: "100%",
          maxWidth: "760px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          backgroundColor: "#f1f5f9",
          borderRadius: "14px",
          padding: "14px 18px",
          border: "1px solid #e2e8f0",
        }}
      >
        <code
          style={{
            flex: 1,
            fontFamily: "monospace",
            fontSize: "13px",
            color: "#334155",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {scriptTag}
        </code>
        <button
          onClick={copyCode}
          style={{
            flexShrink: 0,
            padding: "10px 22px",
            borderRadius: "10px",
            border: "none",
            backgroundColor: copied ? "#16a34a" : "#22c55e",
            color: "white",
            fontWeight: 800,
            fontSize: "13px",
            cursor: "pointer",
            transition: "background-color 0.2s",
            whiteSpace: "nowrap",
          }}
        >
          {copied ? "Copied ✓" : "Copy Code"}
        </button>
      </div>

      {/* ── GO BACK TO DASHBOARD button (untouched position) ── */}
      <button
        onClick={() => (window.location.href = "/dashboard")}
        style={{
          color: "#94a3b8",
          background: "none",
          border: "none",
          fontSize: "10px",
          fontWeight: 900,
          textTransform: "uppercase",
          letterSpacing: "0.4em",
          cursor: "pointer",
          padding: "16px",
          marginTop: "-32px",
        }}
      >
        GO BACK TO DASHBOARD
      </button>

      {/* ── Platform grid ── */}
      <div style={{ width: "100%", maxWidth: "760px" }}>
        <p
          style={{
            fontSize: "13px",
            fontWeight: 900,
            textTransform: "uppercase",
            letterSpacing: "0.2em",
            color: "#64748b",
            textAlign: "center",
            marginBottom: "20px",
          }}
        >
          Deploy in Seconds on Any Platform
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "16px",
          }}
        >
          {PLATFORMS.map((p) => (
            <div
              key={p.name}
              onClick={() => setActivePlatform(p)}
              style={{
                cursor: "pointer",
                border: "1px solid #e5e7eb",
                borderRadius: "10px",
                padding: "20px",
                textAlign: "center",
                backgroundColor: "white",
                transition: "box-shadow 0.2s, transform 0.15s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 16px rgba(0,0,0,0.1)";
                (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
                (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
              }}
            >
              <div style={{ fontSize: "28px", marginBottom: "8px" }}>{p.icon}</div>
              <div style={{ fontSize: "12px", fontWeight: 700, color: "#1e293b" }}>{p.name}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Platform modal ── */}
      {activePlatform && (
        <div
          onClick={() => setActivePlatform(null)}
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: "white",
              borderRadius: "12px",
              padding: "32px",
              maxWidth: "520px",
              width: "90%",
              position: "relative",
            }}
          >
            {/* X close button */}
            <button
              onClick={() => setActivePlatform(null)}
              style={{
                position: "absolute",
                top: "16px",
                right: "16px",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#94a3b8",
                fontSize: "20px",
                lineHeight: 1,
                padding: "4px",
              }}
            >
              ✕
            </button>

            {/* Modal title */}
            <h3 style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a", margin: "0 0 20px" }}>
              How to embed on {activePlatform.name}?
            </h3>

            {/* Steps */}
            <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "14px" }}>
              {activePlatform.steps.map((step, i) => (
                <li key={i} style={{ display: "flex", gap: "14px", alignItems: "flex-start" }}>
                  <span
                    style={{
                      flexShrink: 0,
                      width: "26px",
                      height: "26px",
                      borderRadius: "50%",
                      backgroundColor: "#f1f5f9",
                      border: "1.5px solid #e2e8f0",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "11px",
                      fontWeight: 900,
                      color: "#475569",
                    }}
                  >
                    {i + 1}
                  </span>
                  <span style={{ fontSize: "14px", color: "#334155", lineHeight: 1.6, paddingTop: "3px" }}>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}


export default function BuildPage() {
  const router = useRouter();
  const isRehydrated = useRef(false);
  
  // Helper for namespaced localStorage keys
  const getLSKey = (key: string, id?: string) => {
    return id ? `${key}_${id}` : key;
  };

  const [userEmail, setUserEmail] = useState("");
  const [userInfo, setUserInfo] = useState<any>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [step, setStep] = useState(1);
  const [botId, setBotId] = useState("");
  const [url, setUrl] = useState("");
  const [botName, setBotName] = useState("");
  const [greeting, setGreeting] = useState("");
  const [avatar, setAvatar] = useState("blue");
  const [showChatPreview, setShowChatPreview] = useState(true);

  const [isTrained, setIsTrained] = useState(false);
  const [trainedUrl, setTrainedUrl] = useState("");  // set ONLY after successful /train/url — never on user typing
  const [trainedAt, setTrainedAt] = useState("");
  const [showSuccess, setShowSuccess] = useState(false);
  const [trainingCount, setTrainingCount] = useState(0);
  const [isTraining, setIsTraining] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isKnowledgeModalOpen, setIsKnowledgeModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    avatar: true,
    message: true,
    color: true
  });
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
  const [trainedFaqs, setTrainedFaqs] = useState<any[]>([]);
  const [showTrainedWarning, setShowTrainedWarning] = useState(true);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("dhyey_token");
    router.push("/");
  };

  const API_BASE = "http://localhost:8000";

  // 1. Initial restoration on mount
  useEffect(() => {
    setMounted(true);
    if (typeof window === "undefined") return;

    const urlParams = new URLSearchParams(window.location.search);
    const botIdFromUrl = urlParams.get("bot_id");

    // Handle fresh bot creation session
    if (!botIdFromUrl) {
      // Always clear everything for a new bot session — never reuse old bot from localStorage
      console.log("Creating new chatbot: Clearing stale data.");
      [
        "chatbot_bot_id", "chatbot_trained_url", "chatbot_trained_files",
        "chatbot_trained_faqs", "chatbot_bot_name", "chatbot_greeting",
        "chatbot_color", "chatbot_trained_at", "trained",
        "chatbot_trained_files_", "chatbot_trained_faqs_", "chatbot_trained_url_",
        "chatbot_bot_name_", "chatbot_greeting_", "chatbot_color_",
        "chatbot_trained_at_", "trained_"
      ].forEach(key => localStorage.removeItem(key));

      // Reset all flat/un-namespaced keys as a second safety layer
      localStorage.removeItem("chatbot_trained_faqs");
      localStorage.removeItem("chatbot_trained_files");
      localStorage.removeItem("chatbot_greeting");
      localStorage.removeItem("chatbot_color");
      localStorage.removeItem("chatbot_trained_at");
      localStorage.removeItem("chatbot_trained_url");
      localStorage.removeItem("trained");

      setBotId(""); setUrl(""); setTrainedUrl(""); setIsTrained(false);
      setUploadedFiles([]); setTrainedFaqs([]); setBotName("");
      setGreeting("Hi there! How can I help you today?"); setAvatar("blue");
    }

    // ALWAYS run auth check and user info fetch
    const token = localStorage.getItem("dhyey_token");
    if (!token) {
      router.push("/login");
      return;
    }
    
    axios.get(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => setUserInfo(res.data)).catch(() => { });

    try {
      const payloadStr = atob(token.split(".")[1]);
      const payload = JSON.parse(payloadStr);
      if (payload.email) setUserEmail(payload.email);
    } catch (e) { }

    // IF NEW BOT: Stop rehydration here
    if (!botIdFromUrl) {
      isRehydrated.current = true;
      return;
    }

    // Use botIdFromUrl only — do not fall back to stale localStorage
    const finalBotId = botIdFromUrl || "";

    // IF EXISTING BOT: Perform rehydration
    localStorage.setItem("chatbot_bot_id", finalBotId);
    setBotId(finalBotId);

    // Fetch latest from API
    if (finalBotId && finalBotId.length >= 10) {
      (async () => {
        try {
          const res = await axios.get(`${API_BASE}/bots/${finalBotId}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.data.name) setBotName(res.data.name);
          if (res.data.greeting) setGreeting(res.data.greeting);
          if (res.data.avatar) setAvatar(res.data.avatar);
          if (res.data.id) setIsTrained(true);
        } catch (err: any) {
          if (err.response?.status === 404) {
            console.warn("Bot not found, skipping.");
          } else {
            console.error("Failed to load bot data", err);
          }
        }
      })();
    }

    // Load from localStorage
    const savedBotName = localStorage.getItem(getLSKey("chatbot_bot_name", finalBotId));
    const savedGreeting = localStorage.getItem(getLSKey("chatbot_greeting", finalBotId));
    const savedColor = localStorage.getItem(getLSKey("chatbot_color", finalBotId));

    if (savedBotName) setBotName(savedBotName);
    if (savedGreeting) setGreeting(savedGreeting);
    if (savedColor) setAvatar(savedColor);

    const savedUrl = localStorage.getItem(getLSKey("chatbot_trained_url", finalBotId));
    const savedTrainedAt = localStorage.getItem(getLSKey("chatbot_trained_at", finalBotId));
    
    // Strict guard for files/FAQs rehydration from namespaced keys
    const isValidBotId = typeof finalBotId === "string" && finalBotId.length > 10;
    const savedFilesRaw = isValidBotId ? localStorage.getItem(getLSKey("chatbot_trained_files", finalBotId)) : null;
    const savedFaqsRaw = isValidBotId ? localStorage.getItem(getLSKey("chatbot_trained_faqs", finalBotId)) : null;

    if (savedUrl) {
      setUrl(savedUrl);
      setTrainedUrl(savedUrl);
      setIsTrained(true);
    }
    if (savedTrainedAt) setTrainedAt(savedTrainedAt);
    if (savedFilesRaw) {
      const files = JSON.parse(savedFilesRaw);
      setUploadedFiles([...files]);
      if (files.length > 0) setIsTrained(true);
    }
    if (savedFaqsRaw) {
      const faqs = JSON.parse(savedFaqsRaw);
      setTrainedFaqs([...faqs]);
      if (faqs.length > 0) setIsTrained(true);
    }

    isRehydrated.current = true;
  }, [router]);

  // 2. Auto-save customization settings
  useEffect(() => {
    if (typeof window !== "undefined") {
      // Bug 1: Guard against empty or invalid botId to prevent flat key pollution
      if (!botId || botId.length < 10) return;

      const namespacedBotNameKey = getLSKey("chatbot_bot_name", botId);
      const namespacedGreetingKey = getLSKey("chatbot_greeting", botId);
      const namespacedColorKey = getLSKey("chatbot_color", botId);

      if (botName && botName.trim() !== "") {
        localStorage.setItem(namespacedBotNameKey, botName);
      } else if (botName === "" && !botId) {
        localStorage.removeItem(namespacedBotNameKey);
      }

      if (greeting) localStorage.setItem(namespacedGreetingKey, greeting);
      if (avatar) localStorage.setItem(namespacedColorKey, avatar);
    }
  }, [botName, greeting, avatar, botId, getLSKey]);

  const refreshStateFromLocalStorage = () => {
    const savedUrl = localStorage.getItem(getLSKey("chatbot_trained_url", botId));
    const savedTrainedAt = localStorage.getItem(getLSKey("chatbot_trained_at", botId));
    const savedFilesRaw = localStorage.getItem(getLSKey("chatbot_trained_files", botId));
    const savedFaqsRaw = localStorage.getItem(getLSKey("chatbot_trained_faqs", botId));

    if (savedUrl) {
      setUrl(savedUrl);
      setTrainedUrl(savedUrl);
      setIsTrained(true);
    }
    if (savedTrainedAt) setTrainedAt(savedTrainedAt);
    if (savedFilesRaw) {
      const files = JSON.parse(savedFilesRaw);
      setUploadedFiles([...files]);
      if (files.length > 0) setIsTrained(true);
    }
    if (savedFaqsRaw) {
      const faqs = JSON.parse(savedFaqsRaw);
      setTrainedFaqs([...faqs]);
      if (faqs.length > 0) setIsTrained(true);
    }
  };

  const migrateToNamespaced = (newId: string) => {
    const keysToMigrate = [
      "chatbot_trained_url",
      "chatbot_trained_files",
      "chatbot_trained_faqs",
      "chatbot_bot_name",
      "chatbot_greeting",
      "chatbot_color",
      "chatbot_trained_at",
      "trained"
    ];
    keysToMigrate.forEach(key => {
      const val = localStorage.getItem(key);
      if (val !== null) {
        localStorage.setItem(`${key}_${newId}`, val);
        localStorage.removeItem(key);
      }
    });
    localStorage.setItem("chatbot_bot_id", newId);
  };

  const handleTrain = async () => {
    if (!url) return;

    let finalUrl = url.trim();
    if (finalUrl && !finalUrl.startsWith("http")) {
      finalUrl = "https://" + finalUrl;
    }

    console.log("FINAL URL SENT:", finalUrl);
    setIsTraining(true);
    setTrainProgress(0);
    setTrainingStatus("Starting...");
    let currentBotId = botId;

    try {
      const token = localStorage.getItem("dhyey_token");

      // 1. Create bot if not exists
      if (!currentBotId) {
        console.log("Creating new bot...");
        let initialGreeting = "Hi there! How can I help you today?";
        try {
          const domain = new URL(finalUrl).hostname.replace('www.', '');
          initialGreeting = `Hi! I can answer questions about ${domain}. How can I help?`;
        } catch (e) { }

        const botRes = await axios.post(`${API_BASE}/bots/`, {
          name: botName || "My Chatbot",
          greeting: initialGreeting,
          avatar: "blue"
        }, { headers: { Authorization: `Bearer ${token}` } });
        currentBotId = botRes.data.id;
        console.log("Created bot ID:", botRes.data);
        setBotId(currentBotId);
        migrateToNamespaced(currentBotId);
      }

      // 2. Stream training progress via SSE
      console.log("Training bot via SSE stream...");
      const response = await fetch(`${API_BASE}/train/url/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ bot_id: currentBotId, url: finalUrl }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let chunksStored = 0;
      let trainingError: string | null = null;

      // Read SSE stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n").filter(l => l.startsWith("data: "));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.error) {
              trainingError = data.error;
              break;
            }

            // Update progress bar and status message
            setTrainProgress(data.percent ?? 0);
            setTrainingStatus(data.message ?? "");

            if (data.chunks_stored) {
              chunksStored = data.chunks_stored;
            }

            if (data.done) break;
          } catch (e) {
            console.warn("Failed to parse SSE event:", line);
          }
        }

        if (trainingError) break;
      }

      if (trainingError) {
        throw new Error(trainingError);
      }

      // 3. Post-train state update
      const now = new Date().toISOString();
      localStorage.setItem(getLSKey("chatbot_trained_url", currentBotId), url);
      localStorage.setItem(getLSKey("chatbot_trained_at", currentBotId), now);
      localStorage.setItem(getLSKey("trained", currentBotId), "true");

      setTrainedUrl(url);
      setTrainedAt(now);
      setIsTrained(true);
      try {
        const domain = new URL(finalUrl).hostname.replace('www.', '');
        const domainGreeting = `Hi! I can answer questions about ${domain}. How can I help?`;
        setGreeting(domainGreeting);
        localStorage.setItem(getLSKey("chatbot_greeting", currentBotId), domainGreeting);
      } catch (e) { }
      setTrainingCount(chunksStored);
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);

    } catch (err: any) {
      console.error("Training failed", err);
      setTrainingStatus("Training failed: " + (err.message || "Unknown error"));
    } finally {
      setIsTraining(false);
      setTrainProgress(0);
      console.log("botId:", currentBotId);
    }
  };

  const handleDeleteSource = async () => {
    if (botId) {
      const token = localStorage.getItem("dhyey_token");
      try {
        // 1. Delete old training data
        await axios.delete(`${API_BASE}/train/${botId}`, { headers: { Authorization: `Bearer ${token}` } });

        // 2. Create a BRAND NEW bot for the next training
        const botRes = await axios.post(`${API_BASE}/bots/`, {
          name: botName || "My Chatbot",
          greeting: "Hi there! How can I help you today?",
          avatar: "blue"
        }, { headers: { Authorization: `Bearer ${token}` } });
        const newBotId = botRes.data.id;
        setBotId(newBotId);
        localStorage.setItem("chatbot_bot_id", newBotId);
      } catch (err) {
        console.error("Failed to reset bot", err);
      }
    }

    // 3. Clear all namespaced data for this bot
    localStorage.removeItem(getLSKey("chatbot_trained_url", botId));
    localStorage.removeItem(getLSKey("chatbot_trained_at", botId));
    localStorage.removeItem(getLSKey("chatbot_bot_name", botId));
    localStorage.removeItem(getLSKey("chatbot_greeting", botId));
    localStorage.removeItem(getLSKey("chatbot_color", botId));
    localStorage.removeItem(getLSKey("trained", botId));
    localStorage.removeItem(getLSKey("chatbot_trained_files", botId));
    localStorage.removeItem(getLSKey("chatbot_trained_faqs", botId));
    console.log("All namespaced sources cleared.");

    // 4. Reset ONLY URL-related React state
    setUrl("");
    setTrainedUrl("");
    setIsTrained(false);
    setTrainedAt("");
    setBotName("");
    setGreeting("Hi there! How can I help you today?");
    setAvatar("blue");
    setBotId("");
  };

  const handleUpdateTrainedData = () => {
    // AddKnowledgeModal writes chatbot_bot_id to localStorage after upload.
    // Read it back here so LiveChatPreview receives a valid botId and can make API calls.
    const savedBotId = localStorage.getItem("chatbot_bot_id");
    if (savedBotId && savedBotId.length > 10) {
      // Bug 3: Sync React state with the botId created in the modal
      setBotId(savedBotId);

      const savedFilesRaw = localStorage.getItem(getLSKey("chatbot_trained_files", savedBotId));
      if (savedFilesRaw) {
        const files = JSON.parse(savedFilesRaw);
        setUploadedFiles(files);
        if (files.length > 0) setIsTrained(true);
      }
      const savedFaqsRaw = localStorage.getItem(getLSKey("chatbot_trained_faqs", savedBotId));
      if (savedFaqsRaw) {
        const faqs = JSON.parse(savedFaqsRaw);
        setTrainedFaqs([...faqs]);
        if (faqs.length > 0) setIsTrained(true);
      }
    }
  };

  const handleDeleteFileSource = async (fileName: string) => {
    // Always read from namespaced localStorage
    const currentFilesKey = getLSKey("chatbot_trained_files", botId);
    const currentFilesRaw = localStorage.getItem(currentFilesKey) || "[]";
    const currentFiles = JSON.parse(currentFilesRaw);
    const updatedFiles = currentFiles.filter((f: any) => f.name !== fileName);

    localStorage.setItem(currentFilesKey, JSON.stringify(updatedFiles));
    setUploadedFiles([...updatedFiles]);

    // Call DELETE /train/{bot_id} if this was the last trained item
    const savedUrl = localStorage.getItem(getLSKey("chatbot_trained_url", botId));
    if (updatedFiles.length === 0 && trainedFaqs.length === 0 && !savedUrl && botId) {
      const token = localStorage.getItem("dhyey_token");
      try {
        await axios.delete(`${API_BASE}/train/${botId}`, { headers: { Authorization: `Bearer ${token}` } });
        console.log("Last trained item removed, collection cleared.");
      } catch (err) {
        console.error("Failed to delete collection on last item", err);
      }
    }
  };

  const handleDeleteFaq = async (question: string) => {
    const updatedFaqs = trainedFaqs.filter(f => f.question !== question);
    setTrainedFaqs(updatedFaqs);
    localStorage.setItem(getLSKey("chatbot_trained_faqs", botId), JSON.stringify(updatedFaqs));

    // Also calls DELETE /train/{bot_id} if it's the last item
    const savedUrl = localStorage.getItem(getLSKey("chatbot_trained_url", botId));
    if (updatedFaqs.length === 0 && uploadedFiles.length === 0 && !savedUrl && botId) {
      const token = localStorage.getItem("dhyey_token");
      try {
        await axios.delete(`${API_BASE}/train/${botId}`, { headers: { Authorization: `Bearer ${token}` } });
        console.log("Last trained item removed (FAQ), collection cleared.");
      } catch (err) {
        console.error("Failed to delete collection on last FAQ", err);
      }
    }
  };

  const getDomain = (urlStr: string) => {
    try {
      const domain = new URL(urlStr).hostname;
      return domain;
    } catch {
      return urlStr;
    }
  };

  const handleNextStep1 = () => {
    setStep(2);
  };

  const handleNextStep2 = async () => {
    let currentBotId = botId;
    const token = localStorage.getItem("dhyey_token");
    setIsSaving(true);

    try {
      if (!currentBotId) {
        console.log("Creating new bot in Step 2...");
        const botRes = await axios.post(`${API_BASE}/bots/`, {
          name: botName || "My Chatbot",
          greeting: greeting || "Hi there! How can I help you today?",
          avatar: avatar || "blue"
        }, { headers: { Authorization: `Bearer ${token}` } });
        currentBotId = botRes.data.id;
        console.log("Created bot ID:", botRes.data);
        setBotId(currentBotId);
        migrateToNamespaced(currentBotId);
      } else {
        const isInvalidId = !currentBotId || currentBotId === "null" || currentBotId === "undefined" || currentBotId === "";
        if (isInvalidId) {
          console.warn("Skipping bot update: No valid bot_id available in Step 2.");
        } else {
          console.log("Saving bot customization...");
          try {
            await axios.patch(`${API_BASE}/bots/${currentBotId}`, {
              name: botName,
              avatar: avatar,
              greeting: greeting
            }, { headers: { Authorization: `Bearer ${token}` } });
          } catch (err: any) {
            if (err.response?.status === 404) {
              console.warn("Failed to update bot (404), proceeding to next step anyway.");
            } else {
              throw err;
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Failed to save or create bot settings", err);
    } finally {
      setIsSaving(false);
    }
    setStep(3);
  };

  const copyCode = () => {
    const code = `<script src="http://localhost:3000/widget.js" data-bot-id="${botId || 'BOT_ID_HERE'}"></script>`;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const avatars = [
    { color: 'blue', bg: 'bg-[#3B82F6]', ring: 'ring-[#3B82F6]' },
    { color: 'red', bg: 'bg-[#EF4444]', ring: 'ring-[#EF4444]' },
    { color: 'green', bg: 'bg-[#22C55E]', ring: 'ring-[#22C55E]' },
    { color: 'purple', bg: 'bg-[#8B5CF6]', ring: 'ring-[#8B5CF6]' },
    { color: 'orange', bg: 'bg-[#F59E0B]', ring: 'ring-[#F59E0B]' },
    { color: 'pink', bg: 'bg-[#EC4899]', ring: 'ring-[#EC4899]' },
  ];

  const getInitials = (name: string) => {
    return name ? name.substring(0, 2).toUpperCase() : "AI";
  };

  const [trainingStatus, setTrainingStatus] = useState("");
  const [trainProgress, setTrainProgress] = useState(0);

  useEffect(() => {
    if (!isTraining) {
      setTrainingStatus("");
      setTrainProgress(0);
    }
  }, [isTraining]);

  useEffect(() => {
    // Auto-fill greeting based on URL
    if (step === 1 && url && !botName && !isRehydrated.current) {
      try {
        const domain = new URL(url).hostname.replace('www.', '');
        setGreeting(`Hi! I can answer questions about ${domain}. How can I help?`);
      } catch (e) {
        // Ignore invalid URL
      }
    }
  }, [url, step]);
  if (!mounted) return null;

  return (
    <div
      className="min-h-screen w-full relative isolation-auto text-slate-900 font-sans selection:bg-indigo-100 selection:text-indigo-900 overflow-x-hidden"
      style={{
        backgroundColor: '#f8fafc',
        backgroundImage: `
          radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.35) 0%, transparent 50%),
          radial-gradient(circle at 100% 100%, rgba(59, 130, 246, 0.3) 0%, transparent 50%)
        `,
        backgroundAttachment: 'fixed',
        minHeight: '100vh'
      }}
    >

      {/* 1. FIXED TOP HEADERS (Z-1000) */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
        }}
      >
        {/* Row 1: White Logo Row */}
        <header
          style={{
            width: '100%',
            height: '64px',
            backgroundColor: 'white',
            borderBottom: '1px solid #f1f5f9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 32px'
          }}
        >
          <div className="flex items-center gap-2.5 group cursor-pointer" onClick={() => window.location.href = '/'}>
            <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-100 group-hover:scale-110 transition-transform">
              <Bot className="text-white w-5 h-5" />
            </div>
            <span className="text-2xl font-black tracking-tighter text-slate-900 uppercase">DHYEY</span>
          </div>
          <div className="flex items-center gap-4" ref={dropdownRef} style={{ position: "relative" }}>
            <button
              onClick={() => router.push("/dashboard")}
              style={{
                padding: "8px 16px",
                borderRadius: "10px",
                border: "1.5px solid #e2e8f0",
                backgroundColor: "transparent",
                color: "#475569",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "#cbd5e1";
                e.currentTarget.style.backgroundColor = "#f8fafc";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "#e2e8f0";
                e.currentTarget.style.backgroundColor = "transparent";
              }}
            >
              Dashboard
            </button>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "4px 12px 4px 4px",
                borderRadius: "32px",
                transition: "background-color 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f1f5f9")}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "linear-gradient(135deg, #6366f1, #8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: "bold", fontSize: "14px", flexShrink: 0 }}>
                {userInfo?.name ? userInfo.name.charAt(0).toUpperCase() : <User style={{ width: "14px", height: "14px" }} />}
              </div>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "#334155" }}>{userInfo?.name || userEmail}</span>
            </button>

            {dropdownOpen && (
              <div style={{
                position: "absolute",
                top: "calc(100% + 8px)",
                right: 0,
                width: "220px",
                backgroundColor: "#ffffff",
                borderRadius: "16px",
                boxShadow: "0 10px 25px -5px rgba(0,0,0,0.12), 0 8px 10px -6px rgba(0,0,0,0.08)",
                border: "1px solid #e2e8f0",
                padding: "8px",
                zIndex: 2000,
              }}>
                <div style={{ padding: "12px", borderBottom: "1px solid #f1f5f9", marginBottom: "8px" }}>
                  <p style={{ margin: 0, fontSize: "13px", color: "#0f172a", fontWeight: 700 }}>{userInfo?.name}</p>
                  <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{userInfo?.email}</p>
                </div>
                <button
                  onClick={() => { router.push("/account"); setDropdownOpen(false); }}
                  style={{ width: "100%", display: "flex", alignItems: "center", gap: "10px", padding: "10px 12px", background: "none", border: "none", borderRadius: "8px", color: "#334155", fontSize: "14px", fontWeight: 600, cursor: "pointer", transition: "background-color 0.15s" }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f8fafc")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <Settings style={{ width: "16px", height: "16px" }} />
                  My Account
                </button>
                <button
                  onClick={handleLogout}
                  style={{ width: "100%", display: "flex", alignItems: "center", gap: "10px", padding: "10px 12px", background: "none", border: "none", borderRadius: "8px", color: "#ef4444", fontSize: "14px", fontWeight: 600, cursor: "pointer", transition: "background-color 0.15s" }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#fef2f2")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <LogOut style={{ width: "16px", height: "16px" }} />
                  Log out
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Row 2: Black Step Bar */}
        <div
          style={{
            width: '100%',
            height: '56px',
            backgroundColor: '#000000',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 32px'
          }}
        >
          {/* Back Button */}
          <div className="w-32">
            {step !== 1 && (
              <button
                onClick={() => setStep(Math.max(1, step - 1))}
                className="flex items-center gap-2 text-white font-bold text-[11px] uppercase tracking-[0.2em] hover:text-lime-400 transition-all cursor-pointer"
              >
                <div className="w-7 h-7 rounded-full border border-white/20 flex items-center justify-center">
                  <ChevronLeft className="w-4 h-4" />
                </div>
                <span>BACK</span>
              </button>
            )}
          </div>

          {/* Stepper Center */}
          <div className="flex items-center" style={{ gap: '80px' }}>
            <button
              onClick={() => setStep(1)}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <div className={`rounded-full flex items-center justify-center text-[10px] font-black transition-all ${step === 1 ? 'w-6 h-6 bg-white text-black' : (step > 1 ? 'w-5 h-5 bg-lime-400 text-white' : 'w-6 h-6 border-2 border-gray-400 text-gray-400')} group-hover:scale-110`}>
                {step > 1 ? <Check className="w-3" strokeWidth={4} /> : "1"}
              </div>
              <span className={`text-[10px] font-black uppercase tracking-[0.2em] transition-colors ${step === 1 ? 'text-white' : (step > 1 ? 'text-white' : 'text-gray-400')}`}>TRAIN</span>
            </button>

            <button
              onClick={() => setStep(2)}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <div className={`rounded-full flex items-center justify-center text-[10px] font-black transition-all ${step === 2 ? 'w-6 h-6 bg-white text-black' : (step > 2 ? 'w-5 h-5 bg-lime-400 text-white' : 'w-6 h-6 border-2 border-gray-400 text-gray-400')} group-hover:scale-110`}>
                {step > 2 ? <Check className="w-3" strokeWidth={4} /> : "2"}
              </div>
              <span className={`text-[10px] font-black uppercase tracking-[0.2em] transition-colors ${step === 2 ? 'text-white' : (step > 2 ? 'text-white' : 'text-gray-400')}`}>CHAT</span>
            </button>

            <button
              onClick={() => setStep(3)}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black transition-all ${step === 3 ? 'bg-white text-black' : (step > 3 ? 'bg-lime-400 text-black' : 'border-2 border-gray-400 text-gray-400')} group-hover:scale-110`}>
                {step > 3 ? <Check className="w-3" strokeWidth={4} /> : "3"}
              </div>
              <span className={`text-[10px] font-black uppercase tracking-[0.2em] transition-colors ${step === 3 ? 'text-white' : (step > 3 ? 'text-lime-400' : 'text-gray-400')}`}>DEPLOY</span>
            </button>
          </div>

          {/* Next Button */}
          <div className="w-32 flex justify-end">
            {step !== 3 && (
              <button
                onClick={() => {
                  if (step === 1) handleNextStep1();
                  else if (step === 2) handleNextStep2();
                }}
                disabled={isTraining}
                className="bg-lime-400 hover:bg-white text-black px-5 py-1.5 rounded-full font-black uppercase tracking-widest text-[10px] disabled:opacity-20 transition-all active:scale-95 shadow-lg shadow-lime-400/20 cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <div className="flex flex-col items-center leading-tight">
                    <span className="text-[9px]">NEXT</span>
                    <span className="text-[10px] font-black">STEP</span>
                  </div>
                  <ChevronRight className="w-4 h-4" />
                </div>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2. FIXED SIDEBAR (STEP 2 ONLY) (Z-500) */}
      {step === 2 && (
        <aside
          style={{
            position: 'fixed',
            left: 0,
            top: '120px',
            bottom: 0,
            width: '300px',
            backgroundColor: '#f8f8fb',
            borderRight: '1px solid #e5e7eb',
            zIndex: 500,
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

            {/* Sidebar Header */}
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: '14px' }}>
              {/* Live avatar circle — updates when color swatch is picked */}
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  backgroundColor: avatars.find(a => a.color === avatar)?.bg.replace('bg-[', '').replace(']', '') || '#3B82F6',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                }}
              >
                <span style={{ color: 'white', fontSize: '12px', fontWeight: 900, letterSpacing: '0.05em' }}>AI</span>
              </div>
              <div>
                <h3 style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '0.25em', textTransform: 'uppercase', color: '#0f172a', margin: 0 }}>CUSTOMIZE</h3>
                <p style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600, marginTop: '2px', letterSpacing: '0.05em' }}>Bot appearance</p>
              </div>
            </div>

            {/* Scrollable content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>

              {/* Assistant Name */}
              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', fontSize: '10px', fontWeight: 900, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '8px' }}>ASSISTANT NAME</label>
                <input
                  type="text"
                  value={botName}
                  onChange={(e) => {
                    const newName = e.target.value;
                    setBotName(newName);
                    if (botId) {
                      const token = localStorage.getItem("dhyey_token");
                      axios.patch(`${API_BASE}/bots/${botId}`, {
                        name: newName,
                        avatar: avatar,
                        greeting: greeting
                      }, { headers: { Authorization: `Bearer ${token}` } }).catch(err => console.error(err));
                    }
                  }}
                  placeholder="e.g. My AI Assistant"
                  style={{
                    width: '100%',
                    backgroundColor: 'white',
                    border: '1.5px solid #e2e8f0',
                    borderRadius: '12px',
                    padding: '10px 14px',
                    fontSize: '13px',
                    fontWeight: 600,
                    color: '#0f172a',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              {/* Divider */}
              <div style={{ height: '1px', backgroundColor: '#e5e7eb', marginBottom: '24px' }} />

              {/* Color Scheme */}
              <div>
                <label style={{ display: 'block', fontSize: '10px', fontWeight: 900, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '12px' }}>COLOR SCHEME</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                  {avatars.map((a) => {
                    const hexColor = a.bg.replace('bg-[', '').replace(']', '');
                    const isSelected = avatar === a.color;
                    return (
                      <button
                        key={a.color + '-theme'}
                        onClick={() => setAvatar(a.color)}
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '50%',
                          backgroundColor: hexColor,
                          border: 'none',
                          cursor: 'pointer',
                          position: 'relative',
                          outline: isSelected ? `3px solid ${hexColor}` : '3px solid transparent',
                          outlineOffset: '2px',
                          transform: isSelected ? 'scale(1.15)' : 'scale(1)',
                          transition: 'transform 0.15s ease, outline 0.15s ease',
                          boxShadow: isSelected ? `0 4px 12px ${hexColor}55` : '0 2px 4px rgba(0,0,0,0.12)'
                        }}
                      >
                        {isSelected && (
                          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Check className="w-3 h-3 text-white" strokeWidth={4} />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

            </div>
          </div>
        </aside>
      )}

      {/* 3. FIXED CHAT PREVIEW (STEP 2 ONLY) (Z-2000) */}
      {step === 2 && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 2000,
            width: '420px',
            pointerEvents: 'auto'
          }}
        >
          {showChatPreview ? (
            <div className="animate-in fade-in zoom-in-95 duration-500">
              {/* CHATBOT PREVIEW label */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', paddingRight: '4px' }}>
                <span style={{ fontSize: '9px', fontWeight: 900, letterSpacing: '0.3em', textTransform: 'uppercase', color: '#94a3b8', background: 'white', border: '1px solid #e2e8f0', borderRadius: '999px', padding: '4px 12px' }}>
                  💬 CHATBOT PREVIEW
                </span>
                <span style={{ fontSize: '9px', fontWeight: 700, color: '#86efac', letterSpacing: '0.15em', textTransform: 'uppercase' }}>● LIVE</span>
              </div>
              <LiveChatPreview
                botName={botName}
                avatar={avatar}
                greeting={greeting}
                botId={botId}
                onClose={() => setShowChatPreview(false)}
              />
            </div>
          ) : (
            <button
              onClick={() => setShowChatPreview(true)}
              className="w-16 h-16 bg-black text-white hover:bg-slate-800 rounded-full flex items-center justify-center shadow-2xl transition-all hover:scale-110 active:scale-95 animate-in fade-in zoom-in-50 duration-500 group ml-auto"
            >
              <MessageSquare className="w-8 h-8" />
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-lime-400 rounded-full border-2 border-black animate-pulse"></span>
            </button>
          )}
        </div>
      )}

      {/* 4. MAIN SCROLL AREA (Z-0) */}
      <main
        className="min-h-screen bg-transparent"
        style={{
          paddingLeft: step === 2 ? '300px' : '0'
        }}
      >
        <div style={{ height: '72px' }}></div>
        <div className={`w-full ${step === 2 ? 'h-full flex items-center justify-center p-20' : 'max-w-5xl mx-auto px-6 py-13'}`}>
          {step === 1 && (
            <div className="space-y-6 flex flex-col items-center w-full animate-in fade-in duration-700">
              <div className="space-y-2 text-center">
                <div
                  className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-indigo-900 text-[10px] font-black uppercase tracking-[0.3em] mx-auto shadow-2xl border border-white/10"
                  style={{ backgroundColor: '#dde3f2' }}
                >
                  <span className="text-lime-400">⚡</span> TRAINING PHASE
                </div>
                <h2 className="text-4xl font-bold text-slate-900 leading-tight tracking-tight">Train your chatbot</h2>
                <p className="text-slate-400 text-base font-medium mt-3 max-w-lg mx-auto leading-relaxed">Provide your website URL to help your AI assistant learn about your business.</p>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 pb-16 max-w-2xl mx-auto w-full space-y-4">
                <div className="flex flex-col gap-6">
                  <label className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] block ml-1 text-left">CONTENT SOURCE: WEBSITE URL</label>

                  {isTrained && trainedUrl && !isTraining ? (
                    <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-2xl p-6 group/card">
                      <div className="flex items-center" style={{ gap: '12px' }}>
                        <div className="bg-white border border-slate-200 rounded-2xl flex items-center justify-center shadow-sm" style={{ width: '40px', height: '40px', flexShrink: 0 }}>
                          <Layout className="w-5 h-5 text-indigo-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-3">
                            <h3 className="font-black text-slate-900" style={{ fontSize: '13px', fontWeight: '600' }}>{getDomain(trainedUrl)}</h3>
                            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-600 text-[9px] font-black uppercase tracking-wider">
                              <Check className="w-2.5 h-2.5" /> Trained
                            </span>
                          </div>
                          <p className="font-bold text-slate-400" style={{ fontSize: '11px' }}>
                            Last update: {trainedAt ? new Date(trainedAt).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : ""}
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={handleTrain} className="p-3 bg-white border border-slate-200 rounded-xl hover:text-indigo-600 transition-all" style={{ cursor: 'pointer' }}><RotateCcw className="w-4 h-4" /></button>
                        <button onClick={handleDeleteSource} className="p-3 bg-white border border-slate-200 rounded-xl hover:text-rose-600 transition-all" style={{ cursor: 'pointer' }}><Trash className="w-4 h-4" /></button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-4">
                        <div className="flex-1 flex items-center bg-slate-50 border border-slate-200 rounded-2xl px-6 py-4 focus-within:border-indigo-500/50 transition-all">
                          <Link2 className="w-5 h-5 text-slate-400 mr-4" />
                          <input
                            type="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://your-website.com"
                            className="flex-1 bg-transparent border-none focus:outline-none text-slate-900 font-bold text-sm"
                          />
                        </div>
                        <button onClick={handleTrain} disabled={isTraining} className={`px-10 py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-black uppercase tracking-[0.2em] text-[11px] disabled:opacity-50 transition-all active:scale-95 ${!url.trim() ? 'opacity-40' : 'opacity-100'}`}>
                          {isTraining ? <Loader2 className="w-4 h-4 animate-spin" /> : 'START TRAINING'}
                        </button>
                      </div>
                      <p className="text-[10px] text-gray-400 mt-4 ml-1 tracking-wider uppercase font-bold">• ENTER YOUR WEBSITE TO AUTOMATICALLY EXTRACT CONTENT</p>
                    </div>
                  )}

                  {showSuccess && (
                    <div className="flex items-center gap-2.5 text-emerald-600 font-black text-[10px] uppercase tracking-widest px-2">
                      <Check className="w-4 h-4" /> Successfully trained on {trainingCount} chunks
                    </div>
                  )}

                  {isTraining && (
                    <div className="p-8 bg-indigo-50 border border-indigo-100 rounded-[32px] space-y-5">
                      {/* Status row */}
                      <div className="flex items-center gap-4">
                        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Processing Content</p>
                          <p className="text-indigo-600 text-base font-black truncate">{trainingStatus}</p>
                        </div>
                        <span className="text-indigo-700 font-black text-lg tabular-nums flex-shrink-0">{trainProgress}%</span>
                      </div>
                      {/* Progress bar */}
                      <div className="w-full bg-indigo-100 rounded-full h-2.5 overflow-hidden">
                        <div
                          className="h-2.5 rounded-full bg-indigo-600 transition-all duration-500 ease-out"
                          style={{ width: `${trainProgress}%` }}
                        />
                      </div>
                      {/* Stage labels */}
                      <div className="flex justify-between text-[9px] font-black uppercase tracking-widest text-slate-400">
                        <span className={trainProgress >= 0 ? "text-indigo-500" : ""}>Map</span>
                        <span className={trainProgress >= 15 ? "text-indigo-500" : ""}>Scrape</span>
                        <span className={trainProgress >= 70 ? "text-indigo-500" : ""}>Process</span>
                        <span className={trainProgress >= 80 ? "text-indigo-500" : ""}>Embed</span>
                        <span className={trainProgress >= 95 ? "text-indigo-500" : ""}>Save</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="relative flex justify-center py-1">
                  <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-100"></div></div>
                  <span className="relative bg-white px-6 text-[10px] text-slate-400 font-black tracking-[0.4em]">OR SOURCE FROM</span>
                </div>

                <div className="grid gap-4">
                  {uploadedFiles.map((file, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-[32px] p-6">
                      <div className="flex items-center" style={{ gap: '12px' }}>
                        <div className="flex items-center justify-center" style={{ width: '40px', height: '40px', flexShrink: 0 }}>
                          <FileText className="text-indigo-600" style={{ width: '40px', height: '40px' }} />
                        </div>
                        <div>
                          <h3 className="font-black text-slate-900" style={{ fontSize: '13px', fontWeight: '600' }}>{file.name}</h3>
                          <p className="font-bold text-slate-400" style={{ fontSize: '11px' }}>{file.size} • Trained: {new Date(file.trainedAt).toLocaleDateString()}</p>
                        </div>
                      </div>
                      <button onClick={() => handleDeleteFileSource(file.name)} className="p-3 bg-white border border-slate-200 rounded-xl hover:text-rose-600" style={{ cursor: 'pointer' }}><Trash className="w-4 h-4" /></button>
                    </div>
                  ))}

                  {trainedFaqs.map((faq, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-[32px] p-6">
                      <div className="flex items-center" style={{ gap: '12px' }}>
                        <div className="flex items-center justify-center" style={{ width: '40px', height: '40px', flexShrink: 0 }}>
                          <MessageSquare className="text-indigo-600" style={{ width: '40px', height: '40px' }} />
                        </div>
                        <div>
                          <h3 className="font-black text-slate-900" style={{ fontSize: '13px', fontWeight: '600' }}>{faq.question}</h3>
                          <p className="font-bold text-slate-400" style={{ fontSize: '11px' }}>Trained: {new Date(faq.savedAt).toLocaleDateString()}</p>
                        </div>
                      </div>
                      <button onClick={() => handleDeleteFaq(faq.question)} className="p-3 bg-white border border-slate-200 rounded-xl hover:text-rose-600" style={{ cursor: 'pointer' }}><Trash className="w-4 h-4" /></button>
                    </div>
                  ))}

                  <div onClick={() => setIsKnowledgeModalOpen(true)} className="border-2 border-dashed border-slate-200 rounded-2xl w-full py-8 flex flex-col items-center gap-4 hover:border-indigo-300 hover:bg-indigo-50/20 cursor-pointer transition-all group">
                    <Plus className="w-8 h-8 text-slate-300 group-hover:text-indigo-600 transition-colors" />
                    <div className="text-center">
                      <span className="block font-black text-xs tracking-widest uppercase mb-1">ADD KNOWLEDGE MANUALLY</span>
                      <span className="text-[11px] text-slate-400 font-bold">UPLOAD DOCUMENTS OR FAQS</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="min-h-[50vh]">
              {!isTrained && showTrainedWarning && (
                <div className="fixed bottom-10 left-1/2 -translate-x-1/2 z-[3000] bg-amber-50 border-2 border-amber-400 rounded-2xl px-6 py-4 shadow-lg flex items-center gap-4 max-w-md animate-in slide-in-from-bottom-4 duration-500">
                  <span className="text-amber-500 text-lg">⚠️</span>
                  <div className="flex-1">
                    <p className="font-black text-amber-900 text-sm">Chatbot isn't trained yet.</p>
                    <p className="text-amber-600 text-xs mt-0.5 font-bold">It may not give proper answers until you add knowledge or website URL.</p>
                  </div>
                  <button
                    onClick={() => setShowTrainedWarning(false)}
                    className="p-1.5 hover:bg-amber-100 rounded-lg transition-colors text-amber-900/50 hover:text-amber-900"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <DeployStep botId={botId} copied={copied} copyCode={copyCode} />
          )}
        </div>
      </main>

      <AddKnowledgeModal
        isOpen={isKnowledgeModalOpen}
        onClose={() => setIsKnowledgeModalOpen(false)}
        botId={botId || (typeof window !== "undefined" ? localStorage.getItem("chatbot_bot_id") || "" : "")}
        onUploadSuccess={handleUpdateTrainedData}
      />
    </div>
  );
}
