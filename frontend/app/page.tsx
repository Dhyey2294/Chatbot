"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bot, MessageSquare, Zap, Shield, ArrowRight, X, Send, Globe, Sparkles, Database, Code, Cpu, Layout, HelpCircle, FileText, User } from 'lucide-react';

export default function Home() {
  const router = useRouter();
  const [scrolled, setScrolled] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    // 1. Force Scroll to Top on Refresh
    if (typeof window !== "undefined") {
      window.history.scrollRestoration = "manual";
      window.scrollTo(0, 0);
      if (localStorage.getItem("dhyey_token")) {
        setIsLoggedIn(true);
      }
    }
    
    // 2. Scroll-Shadow Toggle Logic
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };

    // 3. Section Reveal Logic (Observer)
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
    window.addEventListener('scroll', handleScroll);
    
    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("dhyey_token");
    setIsLoggedIn(false);
    router.push("/");
  };

  const handleCreateChatbot = () => {
    const token = localStorage.getItem("dhyey_token");
    if (!token) {
      router.push("/login");
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <div className="relative min-h-screen bg-slate-50/50 text-slate-900 font-sans selection:bg-blue-100 selection:text-blue-900 overflow-x-hidden animate-[fadeIn_0.8s_ease-out]">
      {/* Background Decor */}
      <div className="absolute top-0 inset-x-0 h-[1000px] bg-gradient-to-b from-white to-transparent -z-10" />
      <div className="absolute top-[10%] left-[-10%] w-[600px] h-[600px] bg-indigo-50/40 rounded-full blur-[120px] -z-10" />
      <div className="absolute top-[5%] right-[-5%] w-[400px] h-[400px] bg-blue-50/20 rounded-full blur-[100px] -z-10" />

      {/* Navigation - FIXED TOP */}
      <header className={`fixed top-0 left-0 w-full flex justify-between items-center px-4 md:px-10 py-3.5 z-[1000] border-b transition-all duration-300 ${scrolled ? 'bg-white/80 backdrop-blur-[12px] border-slate-200/60 shadow-md' : 'bg-transparent border-transparent py-4'}`}>
        <div className="flex items-center gap-2.5 group cursor-pointer shrink-0">
          <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-100 group-hover:scale-110 group-hover:rotate-6 transition-transform duration-300">
            <Bot className="text-white w-5 h-5" />
          </div>
          <span className="text-2xl font-black tracking-tighter text-slate-900 uppercase">Dhyey</span>
        </div>
        
        <div className="flex items-center gap-4 lg:gap-10 transition-all text-[10px] font-black uppercase tracking-widest text-slate-400">
          <div className="hidden lg:flex items-center gap-10 mr-4">
            <a href="#features" className="hover:text-indigo-600 hover:scale-105 transition-all">Why Dhyey?</a>
            <a href="#how-it-works" className="hover:text-indigo-600 hover:scale-105 transition-all">How It Works</a>
            <a href="#use-cases" className="hover:text-indigo-600 hover:scale-105 transition-all">Use Cases</a>
          </div>
          <div className="flex items-center gap-3">
            {isLoggedIn ? (
              <>
                <Link 
                  href="/dashboard" 
                  className="px-6 py-2 bg-white border border-slate-200 rounded-full text-slate-700 hover:border-indigo-400 hover:text-indigo-600 hover:shadow-lg hover:scale-[1.03] active:scale-[0.97] transition-all normal-case font-bold"
                >
                  Dashboard
                </Link>
                <button 
                  onClick={handleLogout}
                  className="px-6 py-2 bg-red-500 text-white rounded-full hover:bg-red-600 hover:scale-[1.03] hover:shadow-xl hover:shadow-red-500/20 active:scale-[0.97] transition-all normal-case font-bold cursor-pointer"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link 
                  href="/login" 
                  className="px-6 py-2 bg-white border border-slate-200 rounded-full text-slate-700 hover:border-indigo-400 hover:text-indigo-600 hover:shadow-lg hover:scale-[1.03] active:scale-[0.97] transition-all normal-case font-bold"
                >
                  Login
                </Link>
                <Link 
                  href="/register" 
                  className="px-6 py-2 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 hover:scale-[1.03] hover:shadow-xl hover:shadow-indigo-500/20 active:scale-[0.97] transition-all normal-case font-bold"
                >
                  Sign In
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-[1440px] mx-auto px-6 pt-28 pb-14 bg-white/40 ring-1 ring-slate-100/50 rounded-b-[60px] shadow-sm">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 lg:gap-12 items-center">
          
          {/* LEFT SIDE - Text Content */}
          <div className="text-left space-y-8 animate-in fade-in slide-in-from-left-8 duration-1000">
            <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold backdrop-blur-sm">
              <Zap className="w-3.5 h-3.5 fill-current" />
              <span>THE #1 AI CHATBOT PLATFORM</span>
            </div>

            <h1 className="text-5xl md:text-6xl font-[900] tracking-tight text-slate-900 leading-[1.05] max-w-lg">
              Build AI Chatbots for Any Website in <span className="relative inline-block group">
                <span className="bg-gradient-to-r from-indigo-500 via-blue-600 to-indigo-600 text-transparent bg-clip-text relative z-10 transition-transform group-hover:scale-110">Minutes</span>
                <span className="absolute left-0 bottom-1 w-full h-[12px] bg-indigo-100/60 rounded-full -z-0 blur-[1px] group-hover:h-[15px] transition-all"></span>
              </span>
            </h1>

            <p className="text-xl text-slate-600 max-w-md leading-relaxed font-medium">
              Train on your content, deploy anywhere, and answer users instantly. 
              The smarter way to handle customer support.
            </p>

            <div className="flex flex-col items-start pt-2">
              <button
                onClick={handleCreateChatbot}
                className="group relative w-full sm:w-auto px-10 py-5 bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-full text-lg font-black transition-all duration-300 shadow-lg hover:shadow-[0_20px_60px_rgba(79,70,229,0.35)] hover:scale-[1.05] active:scale-[0.97] flex items-center justify-center gap-3 overflow-hidden cursor-pointer border-none"
              >
                <span className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></span>
                <span className="relative z-10 flex items-center gap-3">
                  Create Your Chatbot
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
                </span>
              </button>
              <p className="text-sm text-gray-400 mt-4 font-bold px-2 tracking-wide uppercase opacity-80">
                No credit card required • 2 min setup
              </p>
            </div>
          </div>

          {/* RIGHT SIDE - Chat Mockup - STABLE BACKGROUND FIX */}
          <div className="relative group animate-in fade-in zoom-in duration-1000 delay-200 transition-all duration-700 hover:scale-[1.02] hover:rotate-[0.5deg]">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.2),transparent_70%)] blur-2xl opacity-100 -z-10"></div>
            
            {/* STABLE GRADIENT: Removed dynamic shift, kept consistent soft gradient */}
            <div className="bg-white/60 backdrop-blur-[12px] border border-white rounded-[40px] p-8 pb-32 h-[560px] w-full relative overflow-hidden shadow-[0_15px_45px_rgba(0,0,0,0.06),0_2px_10px_rgba(0,0,0,0.02)]">
              <div className="mt-20 space-y-4">
                <div className="h-10 w-full bg-white rounded-2xl shadow-sm border border-slate-100/50" />
                <div className="grid grid-cols-2 gap-6 pt-12 opacity-40">
                  <div className="h-32 bg-slate-200 rounded-[32px]" />
                  <div className="h-32 bg-slate-200 rounded-[32px]" />
                </div>
              </div>

              {/* Chat Container: Stable colors ONLY */}
              <div className="absolute bottom-10 right-10 w-[380px] bg-white rounded-[32px] shadow-[0_30px_90px_rgba(0,0,0,0.2)] border border-white/60 flex flex-col overflow-hidden animate-float">
                <div className="bg-gradient-to-r from-indigo-600 via-indigo-500 to-blue-600 p-6 flex items-center justify-between text-white rounded-t-[32px] shadow-lg">
                  <div className="flex items-center gap-4">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-full bg-[#9bbab3] flex items-center justify-center text-white/90 text-sm font-bold border-2 border-white/10 shadow-inner">AI</div>
                      <div className="absolute top-0 -right-0.5 w-3.5 h-3.5 bg-[#00e5ff] border-2 border-indigo-500 rounded-full shadow-lg"></div>
                    </div>
                    <div>
                      <h4 className="text-base font-bold leading-none mb-1.5 tracking-tight">AI Assistant</h4>
                      <div className="text-[10px] text-white/80 font-black uppercase tracking-[0.2em] flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse"></span> Online
                      </div>
                    </div>
                  </div>
                  <X className="w-4 h-4 text-white/40 cursor-pointer hover:text-white transition-colors" />
                </div>

                <div className="p-7 bg-white space-y-6 h-[260px] overflow-y-auto scrollbar-hide">
                  <div className="flex justify-end">
                    <div className="bg-indigo-600 text-white p-4.5 rounded-[22px] rounded-tr-none text-[11px] font-bold max-w-[80%] shadow-xl shadow-indigo-600/15 leading-relaxed">Can you help me choose a product?</div>
                  </div>
                  <div className="flex justify-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-200/50 shrink-0 shadow-inner"></div>
                    <div className="bg-[#f5f1e8] text-slate-800 p-4.5 rounded-[22px] rounded-tl-none text-[11px] font-bold max-w-[80%] border border-[#ece6d9] shadow-sm leading-relaxed">Of course! I can recommend options based on your needs. What are you looking for?</div>
                  </div>
                </div>

                <div className="p-6 bg-slate-50 border-t border-slate-100/50">
                  <div className="flex items-center gap-3 bg-white rounded-full px-5 py-3.5 shadow-sm border border-slate-200/40">
                    <input type="text" placeholder="Ask AI..." autoComplete="off" suppressHydrationWarning={true} className="bg-transparent border-none outline-none text-[11px] flex-1 text-slate-400 font-bold" disabled />
                    <button className="w-9 h-9 bg-teal-500 rounded-full flex items-center justify-center text-white shadow-lg" disabled><Send className="w-3.5 h-3.5 fill-current" /></button>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="absolute top-4 right-4 group-hover:scale-105 transition-transform duration-500">
              <div className="px-6 py-3 bg-gradient-to-r from-blue-700 to-indigo-600 text-white rounded-2xl text-[10px] font-black tracking-widest shadow-2xl flex items-center gap-2 border border-white/20 backdrop-blur-md">
                <MessageSquare className="w-3.5 h-3.5 fill-white" /> NEW CONVERSATION
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* WHY CHOOSE DHYEY SECTION */}
      <section id="features" className="max-w-[1440px] mx-auto px-6 py-14 bg-transparent relative reveal border-t border-slate-200/40 mt-14">
        <div className="text-center mb-12 space-y-3">
          <h2 className="text-4xl md:text-5xl font-black tracking-tighter text-slate-900">Why Choose Dhyey?</h2>
          <p className="text-lg text-slate-500 font-semibold max-w-2xl mx-auto opacity-80 uppercase tracking-widest text-xs">Everything you need for powerful support</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { icon: <Zap className="text-white w-7 h-7" />, title: "Lightning Fast Setup", desc: "Train your chatbot in seconds and deploy instantly with one line of code.", bg: "bg-indigo-600", lightBg: "bg-indigo-50" },
            { icon: <Sparkles className="text-white w-7 h-7" />, title: "Smart AI Responses", desc: "Powered by advanced RAG, your bot provides accurate answers based on your data.", bg: "bg-blue-600", lightBg: "bg-blue-50" },
            { icon: <Globe className="text-white w-7 h-7" />, title: "Works Everywhere", desc: "Embed your chatbot on Shopify, WordPress, or any custom site seamlessly.", bg: "bg-emerald-600", lightBg: "bg-emerald-50" }
          ].map((item, i) => (
            <div key={i} className="group p-8 bg-white border border-slate-100 rounded-[40px] shadow-sm hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 relative overflow-hidden reveal" style={{ transitionDelay: `${i * 100}ms` }}>
              <div className={`absolute top-0 right-0 w-24 h-24 ${item.lightBg} rounded-bl-[60px] -z-10 group-hover:scale-150 transition-all duration-700`}></div>
              <div className={`w-16 h-16 ${item.bg} rounded-3xl flex items-center justify-center mb-7 shadow-lg group-hover:scale-110 group-hover:rotate-6 transition-all`}>
                {item.icon}
              </div>
              <h3 className="text-2xl font-black mb-4 text-slate-900">{item.title}</h3>
              <p className="text-slate-500 font-semibold leading-relaxed tracking-tight opacity-90">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS SECTION */}
      <section id="how-it-works" className="max-w-[1440px] mx-auto px-6 py-14 bg-slate-50/70 border-y border-slate-200/50 rounded-[60px] relative reveal my-14">
        <div className="text-center mb-16 space-y-3">
          <h2 className="text-4xl md:text-5xl font-black tracking-tighter text-slate-900">How It Works</h2>
          <p className="text-lg text-slate-500 font-semibold max-w-2xl mx-auto opacity-70 uppercase tracking-[0.2em] text-[10px]">Get live in just 3 simple steps</p>
        </div>

        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-12 lg:gap-20">
          <div className="hidden md:block absolute top-16 left-[10%] right-[10%] h-1 bg-gradient-to-r from-indigo-200/50 via-blue-200/80 to-indigo-200/50 -z-10 rounded-full"></div>
          {[
            { num: "01", icon: <Database className="w-3.5 h-3.5 text-indigo-500" />, title: "Add Your Data", desc: "Upload documents or provide a URL to train your chatbot instantly." },
            { num: "02", icon: <Cpu className="w-3.5 h-3.5 text-indigo-500" />, title: "Train Your AI", desc: "Our system builds a high-performance knowledge base from your content." },
            { num: "03", icon: <Code className="w-3.5 h-3.5 text-indigo-500" />, title: "Embed Anywhere", desc: "Copy a script and add your chatbot to any website in seconds." }
          ].map((step, i) => (
            <div key={i} className="flex flex-col items-center text-center space-y-7 group reveal" style={{ transitionDelay: `${i * 150}ms` }}>
              <div className="relative">
                <div className="w-18 h-18 bg-white border-2 border-indigo-100 rounded-[32px] flex items-center justify-center text-2xl font-black text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white group-hover:scale-110 group-hover:rotate-[10deg] transition-all duration-300 shadow-lg shadow-indigo-100/50">{step.num}</div>
                <div className="absolute -top-2 -right-2 w-7 h-7 bg-white rounded-full flex items-center justify-center shadow-md group-hover:scale-125 transition-all">{step.icon}</div>
              </div>
              <div className="space-y-4">
                <h3 className="text-2xl font-black text-slate-900">{step.title}</h3>
                <p className="text-slate-500 font-semibold leading-relaxed max-w-[280px] opacity-90">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* USE CASES SECTION */}
      <section id="use-cases" className="max-w-[1440px] mx-auto px-6 py-14 bg-transparent relative reveal my-14">
        <div className="text-center mb-14 space-y-3">
          <h2 className="text-4xl md:text-5xl font-black tracking-tighter text-slate-900">Use Cases</h2>
          <p className="text-lg text-slate-500 font-semibold max-w-2xl mx-auto opacity-70 uppercase tracking-widest text-[10px]">Powerful AI for every project</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {[
            { icon: <HelpCircle className="w-6 h-6 text-indigo-600" />, title: "Customer Support", desc: "Answer queries instantly and reduce support workload effortlessly." },
            { icon: <Zap className="w-6 h-6 text-blue-600" />, title: "E-commerce Assistant", desc: "Help users find products, recommend items, and boost conversions." },
            { icon: <FileText className="w-6 h-6 text-indigo-600" />, title: "Documentation Bot", desc: "Turn your docs into an AI assistant that answers questions instantly." },
            { icon: <User className="w-6 h-6 text-blue-600" />, title: "Personal Projects", desc: "Build custom AI bots for your own websites, portfolios, and ideas." }
          ].map((item, i) => (
            <div key={i} className="group p-9 bg-white border border-slate-200/70 rounded-[40px] hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] hover:border-indigo-400/30 transition-all duration-300 reveal" style={{ transitionDelay: `${i * 100}ms` }}>
              <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mb-7 shadow-inner group-hover:bg-indigo-50 group-hover:scale-110 group-hover:rotate-3 transition-all">
                {item.icon}
              </div>
              <h3 className="text-2xl font-black mb-4 text-slate-900">{item.title}</h3>
              <p className="text-slate-500 font-semibold leading-relaxed tracking-tight opacity-90">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Social Proof Stats */}
      <section className="bg-white/60 py-14 px-6 relative z-10 border-t border-slate-200/50 rounded-t-[60px] reveal">
        <div className="max-w-[1440px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
          {[
            { label: "Active Bots", value: "5,000+" },
            { label: "Messages Handled", value: "2M+" },
            { label: "Support Hours Saved", value: "50k+" }
          ].map((stat, i) => (
            <div key={i} className="space-y-2 transition-all hover:scale-105 duration-300 reveal" style={{ transitionDelay: `${i * 150}ms` }}>
              <p className="text-5xl font-black bg-gradient-to-r from-indigo-600 to-blue-600 text-transparent bg-clip-text drop-shadow-sm tracking-tighter">{stat.value}</p>
              <p className="text-slate-400 font-black uppercase tracking-[0.3em] text-[10px] opacity-80">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="w-full bg-slate-50 border-t border-slate-200/60 transition-all">
        <div className="max-w-[1440px] mx-auto px-10 py-16">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-16 lg:gap-24">
            <div className="space-y-7">
              <div className="flex items-center gap-3 group shrink-0">
                <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg group-hover:rotate-12 transition-transform">
                  <Bot className="text-white w-6 h-6" />
                </div>
                <span className="text-2xl font-black tracking-tighter text-slate-900 uppercase">Dhyey</span>
              </div>
              <p className="text-sm text-slate-500 font-bold max-w-[240px] leading-relaxed opacity-80">
                The world's simplest AI chatbot platform. Transform your visitor experience in seconds.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-12">
              <div className="space-y-7">
                <h4 className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-800 opacity-60">Product</h4>
                <ul className="space-y-4">
                  {['Features', 'Pricing', 'Use Cases'].map((link) => (
                    <li key={link}><a href={`#${link.toLowerCase().replace(' ', '-')}`} className="text-sm text-slate-500 font-bold hover:text-indigo-600 hover:ml-1 transition-all"># {link}</a></li>
                  ))}
                </ul>
              </div>
              <div className="space-y-7">
                <h4 className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-800 opacity-60">Company</h4>
                <ul className="space-y-4">
                  {['About', 'Contact'].map((link) => (
                    <li key={link}><a href="#" className="text-sm text-slate-500 font-bold hover:text-indigo-600 hover:ml-1 transition-all"># {link}</a></li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="flex items-start md:items-end md:justify-end">
              <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest opacity-60">
                © 2026 Dhyey. Modern AI Support.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
