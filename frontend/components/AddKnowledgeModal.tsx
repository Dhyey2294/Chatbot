'use client';

import React, { useState } from 'react';
import axios from 'axios';
import { X, FileText, MessageSquare, Upload, ArrowLeft, Loader2, Plus, Trash2, CheckCircle2 } from 'lucide-react';

const UPLOAD_STAGES = [
  { title: "UPLOADING DOCUMENT...", sub: "Transferring your file to the knowledge engine." },
  { title: "EXTRACTING TEXT...", sub: "Reading and parsing document contents." },
  { title: "ANALYZING CONTENT...", sub: "Understanding the structure and meaning." },
  { title: "CHUNKING KNOWLEDGE...", sub: "Breaking content into intelligent segments." },
  { title: "INJECTING INTO MEMORY...", sub: "Embedding knowledge into vector space." },
  { title: "FINALIZING TRAINING...", sub: "Almost done! Saving to your chatbot." },
];

interface AddKnowledgeModalProps {
  isOpen: boolean;
  onClose: () => void;
  botId?: string;
  onUploadSuccess?: () => void;
}

type ModalView = 'main' | 'upload' | 'faq' | 'loading';

export default function AddKnowledgeModal({ isOpen, onClose, botId, onUploadSuccess }: AddKnowledgeModalProps) {
  const [view, setView] = useState<ModalView>('main');
  const [faq, setFaq] = useState({ question: '', answer: '' });
  const [files, setFiles] = useState<File[]>([]);
  const [loadingStage, setLoadingStage] = useState(0);

  if (!isOpen) return null;

  const handleSave = async () => {
    let currentBotId = botId;

    // Helper to create bot if it doesn't exist
    const ensureBotCreated = async (context: string) => {
      if (!currentBotId) {
        console.log(`Creating new bot for ${context}...`);
        try {
          const botRes = await axios.post('http://127.0.0.1:8000/bots/', {
            name: "My Bot",
            greeting: "Hi there! How can I help you today?",
            avatar: "blue",
            owner_email: "user@chatbot.com"
          });
          currentBotId = botRes.data.id;
          localStorage.setItem('chatbot_bot_id', currentBotId || '');
          return true;
        } catch (err) {
          console.error("Bot creation failed", err);
          alert("Failed to initialize bot for training. Please check the backend connection.");
          return false;
        }
      }
      return true;
    };

    if (view === 'upload' && files.length > 0) {
      if (!(await ensureBotCreated('knowledge upload'))) return;

      setView('loading');
      setLoadingStage(0);
      let timedOut = false;

      // Stage progression timers
      const timers: ReturnType<typeof setTimeout>[] = [
        setTimeout(() => setLoadingStage(1), 2000),
        setTimeout(() => setLoadingStage(2), 5000),
        setTimeout(() => setLoadingStage(3), 9000),
        setTimeout(() => setLoadingStage(4), 13000),
        setTimeout(() => setLoadingStage(5), 17000),
      ];

      // 60-second timeout fallback
      const timeoutId = setTimeout(() => {
        timedOut = true;
        setView('upload');
        alert('Upload timed out. Please try again.');
      }, 60000);

      try {
        const uploadedInfos = [];
        for (const file of files) {
          if (timedOut) break;

          const formData = new FormData();
          formData.append('bot_id', currentBotId || '');
          formData.append('file', file);

          const response = await axios.post('http://127.0.0.1:8000/train/file', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });

          if (response.data.status === 'success') {
            uploadedInfos.push({
              name: file.name,
              size: (file.size / 1024).toFixed(1) + ' KB',
              trainedAt: new Date().toISOString(),
            });
          }
        }

        if (!timedOut) {
          // Save to localStorage
          const existingFilesRaw = localStorage.getItem('chatbot_trained_files');
          const existingFiles = existingFilesRaw ? JSON.parse(existingFilesRaw) : [];
          const newFileList = [...existingFiles, ...uploadedInfos];
          localStorage.setItem('chatbot_trained_files', JSON.stringify(newFileList));
          localStorage.setItem('chatbot_bot_id', currentBotId || '');

          onUploadSuccess?.();
          onClose();
          setView('main');
          setFiles([]);
        }
      } catch (err) {
        console.error("Upload failed", err);
        if (!timedOut) {
          alert("Failed to upload some files. Please check the backend connection.");
          setView('upload');
        }
      } finally {
        // Clear ALL timers to prevent state updates after unmount
        timers.forEach(clearTimeout);
        clearTimeout(timeoutId);
        setLoadingStage(0);
      }
    } else if (view === 'faq') {
      const effectiveBotId = botId || localStorage.getItem("chatbot_bot_id") || "";
      if (!effectiveBotId) {
        alert("Please train a URL first before adding FAQs.");
        return;
      }
      if (!faq.question.trim()) {
        alert("Please enter a question");
        return;
      }
      if (!faq.answer.trim()) {
        alert("Please enter an answer");
        return;
      }

      setView('loading');
      try {
        const response = await axios.post('http://localhost:8000/train/faq', {
          bot_id: effectiveBotId,
          faqs: [{ question: faq.question.trim(), answer: faq.answer.trim() }]
        }, {
          headers: {
            'Content-Type': 'application/json'
          }
        });

        const existing = JSON.parse(localStorage.getItem("chatbot_trained_faqs") || "[]");
        existing.push({ question: faq.question.trim(), answer: faq.answer.trim(), savedAt: new Date().toISOString() });
        localStorage.setItem("chatbot_trained_faqs", JSON.stringify(existing));
        onUploadSuccess?.();
        setView('main');
        setFaq({ question: '', answer: '' });
        onClose();
      } catch (err: any) {
        console.error("FAQ save failed", err);
        alert("Failed to save FAQ: " + err.message);
        setView('faq');
      }
    } else {
      onClose();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xl z-[100] flex items-center justify-center p-6 pt-32 animate-in fade-in duration-300">
      <div className="bg-white border border-slate-200 rounded-[40px] w-full max-w-2xl shadow-[0_30px_100px_rgba(0,0,0,0.15)] relative group animate-in zoom-in-95 duration-300 overflow-hidden" style={{ maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>

        {/* Header Decorator */}
        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-indigo-500 via-blue-500 to-emerald-500 rounded-t-[40px] overflow-hidden"></div>

        {/* Modal Header */}
        <div className="p-10 pb-4 flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-3xl font-[900] tracking-tighter text-slate-900 uppercase">
              {view === 'main' && 'Add Knowledge'}
              {view === 'upload' && 'Upload Document'}
              {view === 'faq' && 'Add FAQ Item'}
              {view === 'loading' && 'Injecting Intelligence'}
            </h3>
            {view !== 'loading' && (
              <p className="text-slate-400 font-bold uppercase tracking-[0.2em] text-[10px]">
                {view === 'main' && 'Inject new intelligence into your assistant'}
                {view === 'upload' && 'Sync offline documents to your knowledge base'}
                {view === 'faq' && 'Manual training for specific edge cases'}
              </p>
            )}
          </div>
          {view !== 'loading' && (
            <button
              onClick={() => { setView('main'); setFiles([]); setFaq({ question: '', answer: '' }); onClose(); }}
              className="w-10 h-10 bg-slate-50 hover:bg-slate-100 rounded-full flex items-center justify-center transition-all group/close"
            >
              <X className="w-5 h-5 text-slate-400 group-hover/close:text-slate-900" />
            </button>
          )}
        </div>

        {/* Modal Content — scrollable area */}
        <div className="p-10 pt-6 flex flex-col min-h-0" style={{ overflowY: 'auto', flex: 1 }}>

          {view === 'main' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-8 duration-500">
              <div
                onClick={() => setView('upload')}
                className="bg-white border-4 border-slate-50 hover:border-indigo-100 hover:shadow-2xl hover:-translate-y-2 rounded-[32px] p-10 flex flex-col items-center text-center gap-6 cursor-pointer transition-all group/card"
              >
                <div className="w-20 h-20 bg-slate-50 rounded-[24px] flex items-center justify-center shadow-sm group-hover/card:bg-indigo-600 group-hover/card:rotate-6 group-hover/card:scale-110 transition-all duration-500">
                  <FileText className="w-10 h-10 text-slate-400 group-hover/card:text-white" />
                </div>
                <div className="space-y-2">
                  <h4 className="text-xl font-black text-slate-900 tracking-tightest uppercase">Upload Document</h4>
                  <p className="text-xs font-bold text-slate-400 leading-relaxed px-2 uppercase tracking-wide">Sync PDFs, Docx or Text files instantly</p>
                </div>
              </div>

              <div
                onClick={() => setView('faq')}
                className="bg-white border-4 border-slate-50 hover:border-blue-100 hover:shadow-2xl hover:-translate-y-2 rounded-[32px] p-10 flex flex-col items-center text-center gap-6 cursor-pointer transition-all group/card"
              >
                <div className="w-20 h-20 bg-slate-50 rounded-[24px] flex items-center justify-center shadow-sm group-hover/card:bg-blue-600 group-hover/card:rotate-6 group-hover/card:scale-110 transition-all duration-500">
                  <MessageSquare className="w-10 h-10 text-slate-400 group-hover/card:text-white" />
                </div>
                <div className="space-y-2">
                  <h4 className="text-xl font-black text-slate-900 tracking-tightest uppercase">Add static FAQ</h4>
                  <p className="text-xs font-bold text-slate-400 leading-relaxed px-2 uppercase tracking-wide">Train AI on common questions & answers</p>
                </div>
              </div>
            </div>
          )}

          {view === 'upload' && (
            <div className="space-y-8 animate-in fade-in slide-in-from-right-8 duration-500">
              <div className="relative group/upload">
                <input
                  type="file"
                  multiple
                  className="absolute inset-0 opacity-0 cursor-pointer z-10"
                  onChange={handleFileChange}
                />
                <div className="border-4 border-dashed border-slate-100 bg-slate-50/50 rounded-[32px] py-8 flex flex-col items-center justify-center text-center gap-6 group-hover/upload:border-indigo-200 group-hover/upload:bg-white transition-all">
                  <div className="w-20 h-20 bg-white shadow-xl rounded-[24px] flex items-center justify-center group-hover/upload:scale-110 transition-all duration-500">
                    <Upload className="w-10 h-10 text-indigo-500" />
                  </div>
                  <div className="space-y-2">
                    <p className="text-slate-900 font-black text-xl uppercase tracking-tighter">Choose Knowledge Media</p>
                    <p className="text-slate-400 font-black uppercase tracking-[0.2em] text-[10px]">Drag and drop files here or click to browse</p>
                  </div>
                </div>
              </div>

              {files.length > 0 && (
                <div className="space-y-3">
                  <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 px-1">Selected Files</p>
                  <div className="grid grid-cols-1 gap-3">
                    {files.map((file, idx) => (
                      <div key={idx} className="bg-slate-50 rounded-2xl p-4 flex items-center justify-between border border-slate-100">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-sm">
                            <FileText className="w-5 h-5 text-indigo-500" />
                          </div>
                          <div className="space-y-0.5">
                            <p className="text-xs font-black text-slate-900 truncate max-w-[200px]">{file.name}</p>
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{(file.size / 1024).toFixed(1)} KB</p>
                          </div>
                        </div>
                        <button
                          onClick={() => setFiles(files.filter((_, i) => i !== idx))}
                          className="w-8 h-8 hover:bg-rose-50 rounded-lg flex items-center justify-center transition-all group/del"
                          style={{ cursor: 'pointer' }}
                        >
                          <Trash2 className="w-4 h-4 text-slate-300 group-hover/del:text-rose-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {view === 'faq' && (
            <div className="space-y-8 animate-in fade-in slide-in-from-right-8 duration-500">
              <div className="space-y-6">
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] px-1">Question</label>
                  <input
                    type="text"
                    placeholder="e.g. What is your refund policy?"
                    className="w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-6 py-5 text-slate-900 placeholder:text-slate-300 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-bold text-lg"
                    value={faq.question}
                    onChange={(e) => setFaq({ ...faq, question: e.target.value })}
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] px-1">Answer</label>
                  <textarea
                    rows={4}
                    placeholder="Describe the response clearly..."
                    className="w-full bg-slate-50/50 border border-slate-200 rounded-2xl px-6 py-5 text-slate-900 placeholder:text-slate-300 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-bold text-lg resize-none"
                    value={faq.answer}
                    onChange={(e) => setFaq({ ...faq, answer: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}

          {view === 'loading' && (
            <div className="p-16 flex flex-col items-center justify-center text-center gap-10 animate-in fade-in zoom-in-95 duration-700">
              <div className="relative">
                <div className="w-32 h-32 bg-indigo-50 rounded-[40px] flex items-center justify-center relative z-10">
                  <Loader2 className="w-16 h-16 text-indigo-600 animate-spin" />
                </div>
                <div className="absolute inset-0 bg-indigo-500/20 blur-[40px] rounded-full animate-pulse"></div>
              </div>
              <div className="space-y-4">
                <p className="text-3xl font-[900] tracking-tightest text-slate-900 uppercase" style={{ transition: 'opacity 0.4s ease', opacity: 1 }}>
                  {UPLOAD_STAGES[loadingStage]?.title ?? 'PROCESSING...'}
                </p>
                <p className="text-slate-400 text-[11px] font-black uppercase tracking-[0.3em] max-w-sm mx-auto leading-relaxed">
                  {UPLOAD_STAGES[loadingStage]?.sub ?? 'Please wait.'}
                </p>
              </div>
            </div>
          )}

        </div>

        {/* Footer Controls — pinned outside scroll, always visible */}
        {view !== 'main' && view !== 'loading' && (
          <div className="px-10 pb-8 pt-4 flex justify-between items-center border-t border-slate-100 animate-in fade-in slide-in-from-top-6 duration-500 delay-200" style={{ flexShrink: 0 }}>
            <button
              onClick={() => setView('main')}
              className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 hover:text-slate-900 transition-all group/back"
            >
              <ArrowLeft className="w-4 h-4 group-hover/back:-translate-x-1 transition-transform" /> Back to source
            </button>
            <button
              onClick={handleSave}
              className="bg-slate-900 text-white px-12 py-5 rounded-2xl font-black uppercase tracking-widest text-[10px] hover:bg-slate-800 transition-all shadow-xl active:scale-95 flex items-center gap-3"
            >
              Save Knowledge <Plus className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
