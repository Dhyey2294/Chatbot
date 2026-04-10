"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Send, Bot, User, Loader2, X, Sparkles, RotateCcw, MessageSquare } from "lucide-react";

interface Message {
  role: "user" | "bot";
  content: string;
  images?: Array<{ url: string; source_url: string } | string>;
}

interface LiveChatPreviewProps {
  botName: string;
  avatar: string;
  greeting: string;
  botId: string;
  onClose?: () => void;
}

export default function LiveChatPreview({ botName, avatar, greeting, botId, onClose }: LiveChatPreviewProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [mounted, setMounted] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [quickQuestions, setQuickQuestions] = useState<string[]>(["What can you do?"]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    setMounted(true);

    // Build quick-reply chips dynamically from trained sources
    const chips: string[] = ["What can you do?"];
    if (typeof window !== "undefined") {
      const hasUrl = !!localStorage.getItem("chatbot_trained_url");
      const hasFiles = JSON.parse(localStorage.getItem("chatbot_trained_files") || "[]").length > 0;
      if (hasUrl) chips.push("Tell me about this website");
      if (hasFiles) chips.push("Tell me about this document");
    }
    setQuickQuestions(chips);
  }, []);

  // Theme configuration based on avatar color
  const themes: {
    [key: string]: {
      primary: string;
      gradient: string;
      shadow: string;
      glow: string;
    }
  } = {
    blue: {
      primary: "bg-[#3B82F6]",
      gradient: "bg-gradient-to-r from-[#3B82F6] to-[#2563EB]",
      shadow: "shadow-blue-200",
      glow: "rgba(59, 130, 246, 0.1)"
    },
    red: {
      primary: "bg-[#EF4444]",
      gradient: "bg-gradient-to-r from-[#EF4444] to-[#DC2626]",
      shadow: "shadow-red-200",
      glow: "rgba(239, 68, 68, 0.1)"
    },
    green: {
      primary: "bg-[#22C55E]",
      gradient: "bg-gradient-to-r from-[#22C55E] to-[#16A34A]",
      shadow: "shadow-emerald-200",
      glow: "rgba(34, 197, 94, 0.1)"
    },
    purple: {
      primary: "bg-[#8B5CF6]",
      gradient: "bg-gradient-to-r from-[#8B5CF6] to-[#7C3AED]",
      shadow: "shadow-purple-200",
      glow: "rgba(139, 92, 246, 0.1)"
    },
    orange: {
      primary: "bg-[#F59E0B]",
      gradient: "bg-gradient-to-r from-[#F59E0B] to-[#D97706]",
      shadow: "shadow-amber-200",
      glow: "rgba(245, 158, 11, 0.1)"
    },
    pink: {
      primary: "bg-[#EC4899]",
      gradient: "bg-gradient-to-r from-[#EC4899] to-[#DB2777]",
      shadow: "shadow-pink-200",
      glow: "rgba(236, 72, 153, 0.1)"
    },
  };

  const activeTheme = themes[avatar] || themes.blue;

  // Initial greeting message - initialized only once
  useEffect(() => {
    if (!initializedRef.current) {
      const effectiveBotName = botName || "Assistant";
      const effectiveGreeting = greeting || `Hi there! 👋 I'm ${effectiveBotName}. How can I help you today?`;
      setMessages([{ role: "bot", content: effectiveGreeting }]);
      initializedRef.current = true;
    }
  }, [greeting, botName]);

  // Scroll to bottom whenever messages or typing state changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages, isTyping]);

  const clearChat = () => {
    const effectiveBotName = botName || "Assistant";
    const effectiveGreeting = greeting || `Hi there! 👋 I'm ${effectiveBotName}. How can I help you today?`;
    setMessages([{ role: "bot", content: effectiveGreeting }]);
  };

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || isLoading) return;


    if (!text) setInput("");
    setMessages((prev) => [...prev, { role: "user", content: messageText }]);

    if (!botId) {
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        setMessages((prev) => [...prev, { role: "bot", content: "Please complete the training step first." }]);
      }, 1500);
      return;
    }

    setIsLoading(true);
    console.log("Using bot_id for chat:", botId);

    // Slight delay before "Typing..." starts for realism
    setTimeout(async () => {
      setIsTyping(true);

      try {
        const token = localStorage.getItem("dhyey_token");
        const headers = token ? { Authorization: `Bearer ${token}` } : {};

        const response = await axios.post(`http://127.0.0.1:8000/chat/${botId}`, {
          question: messageText,
        }, { headers });

        // Minimum typing duration for realism
        setTimeout(() => {
          setIsTyping(false);
          setMessages((prev) => [...prev, {
            role: "bot",
            content: response.data.answer,
            images: response.data.images || [],
          }]);
          setIsLoading(false);
        }, 1000);
      } catch (error: any) {
        console.error("API ERROR:", error.response || error.message);
        setIsTyping(false);
        setMessages((prev) => [...prev, {
          role: "bot",
          content: "I'm not connected yet. Please make sure the backend is running."
        }]);
        setIsLoading(false);
      }
    }, 500);
  };

  const QuickStart = () => {
    if (messages.length > 1) return null;
    return (
      <div className="flex flex-wrap gap-2 mt-4 px-2 animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-500">
        {quickQuestions.map((q, i) => (
          <button
            key={i}
            onClick={() => handleSend(q)}
            className="text-[10px] font-bold text-slate-500 bg-white border border-slate-200 rounded-full px-4 py-2 hover:border-indigo-400 hover:text-indigo-600 hover:shadow-md transition-all active:scale-95 text-left"
          >
            {q}
          </button>
        ))}
      </div>
    );
  };

  const getInitials = (name: string) => {
    return name ? name.substring(0, 2).toUpperCase() : "AI";
  };

  if (!mounted) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[9999] w-[400px] max-w-[calc(100vw-3rem)] h-[540px] max-h-[calc(100vh-3rem)] bg-white rounded-[40px] shadow-[0_40px_100px_rgba(0,0,0,0.12)] overflow-hidden flex flex-col border border-slate-100/50 animate-in fade-in zoom-in-95 duration-700 group">
      {/* Dynamic Glow Layer */}
      <div
        className="absolute inset-0 pointer-events-none transition-colors duration-1000 -z-10"
        style={{ backgroundColor: activeTheme.glow }}
      ></div>

      {/* Header Upgrade */}
      <div className={`h-[90px] p-8 ${activeTheme.gradient} text-white flex items-center justify-between shadow-xl relative overflow-hidden transition-all duration-700`}>
        {/* Header Decoration */}
        <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-black/5 rounded-full blur-2xl translate-y-1/2 -translate-x-1/2"></div>

        <div className="flex items-center gap-4 relative z-10">
          <div className="w-12 h-12 rounded-[18px] bg-white/20 backdrop-blur-md flex items-center justify-center font-black text-lg border border-white/20 shadow-inner group-hover:rotate-6 transition-transform duration-500">
            {getInitials(botName)}
          </div>
          <div>
            <h4 className="text-base font-black tracking-tight leading-none mb-2">{botName || "Assistant"}</h4>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-lime-400 rounded-full animate-pulse shadow-[0_0_10px_rgba(163,230,53,0.8)] border border-lime-300"></span>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] opacity-90 drop-shadow-sm">ONLINE & ACTIVE</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 relative z-10">
          <button
            onClick={clearChat}
            disabled={messages.length <= 1}
            className="p-2 hover:bg-white/20 rounded-xl transition-all text-white/70 hover:text-white disabled:opacity-20 active:scale-90"
            title="Reset conversation"
          >
            <RotateCcw size={18} />
          </button>
          <div className="h-6 w-[1px] bg-white/20 mx-1"></div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-xl transition-all text-white/70 hover:text-white active:scale-90"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Scrollable Chat Area */}
      <div ref={scrollRef} className="flex-1 p-5 space-y-4 overflow-y-auto bg-slate-50/30 scroll-smooth flex flex-col pt-6 font-sans">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-[fadeIn_0.5s_ease-out]`}
          >
            {msg.role === "bot" && (
              <div className={`w-8 h-8 rounded-xl ${activeTheme.primary} flex items-center justify-center text-white shrink-0 mr-2.5 shadow-lg group-hover:rotate-12 transition-transform duration-500`}>
                <Sparkles size={14} />
              </div>
            )}
            <div className={`max-w-[80%] ${msg.role === "user" ? "" : ""}`}>
              <div className={`p-3.5 rounded-2xl text-[13px] font-semibold leading-relaxed shadow-sm hover:shadow-md transition-all duration-300 ${msg.role === "user"
                ? `${activeTheme.gradient} text-white rounded-tr-none ${activeTheme.shadow}`
                : "bg-white text-slate-700 border border-slate-200/60 rounded-tl-none"
                }`}>
                {msg.content}
              </div>
              {msg.role === "bot" && msg.images && msg.images.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "8px" }}>
                  {msg.images.map((item, imgIdx) => {
                    const imgUrl = typeof item === "object" ? item.url : item;
                    const linkUrl = typeof item === "object" && item.source_url ? item.source_url : imgUrl;
                    return (
                      <a key={imgIdx} href={linkUrl} target="_blank" rel="noopener noreferrer">
                        <img
                          src={imgUrl}
                          alt="Product image"
                          style={{
                            maxWidth: "160px",
                            maxHeight: "160px",
                            objectFit: "cover",
                            borderRadius: "8px",
                            cursor: "pointer",
                            border: "1px solid #e2e8f0",
                          }}
                        />
                      </a>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing Animation */}
        {isTyping && (
          <div className="flex justify-start animate-[fadeIn_0.3s_ease-out]">
            <div className={`w-8 h-8 rounded-xl ${activeTheme.primary} flex items-center justify-center text-white shrink-0 mr-2.5 shadow-lg`}>
              <Bot size={14} />
            </div>
            <div className="bg-white border border-slate-200/60 p-4 rounded-2xl rounded-tl-none shadow-sm flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce"></span>
              <span className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce delay-150"></span>
              <span className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce delay-300"></span>
            </div>
          </div>
        )}

        <QuickStart />
      </div>

      {/* Input Box Upgrade */}
      <div className="p-4 bg-white border-t border-slate-100">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="relative flex items-center group/input"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="w-full bg-slate-50 border border-slate-200 rounded-full pl-6 pr-14 py-3 text-sm font-semibold text-slate-900 placeholder:text-slate-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-400 transition-all duration-300"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={`absolute right-1.5 w-10 h-10 ${activeTheme.gradient} rounded-full flex items-center justify-center text-white shadow-lg transition-all duration-300 hover:scale-110 active:scale-95 disabled:opacity-30 disabled:hover:scale-100 transform`}
          >
            <Send size={16} className="ml-0.5" />
          </button>
        </form>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

    </div>
  );
}
