import React, { memo, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  BrainCircuit,
  ChevronDown,
  Clock3,
  FileStack,
  Loader2,
  MessageSquare,
  Send,
} from 'lucide-react';
import { FREE_MODELS } from '../models';

const MessageCard = memo(function MessageCard({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-rise`}>
      <div className={`message-card ${isUser ? 'message-user' : 'message-assistant'} ${message.error ? 'message-error' : ''}`}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-300">
              {isUser ? 'You' : 'Response'}
            </span>
            {message.actualModel && !isUser && (
              <span className="text-[11px] text-cyan-200">{message.actualModel}</span>
            )}
          </div>
          {message.metrics?.latency_ms && (
            <span className="text-[11px] text-slate-400">{message.metrics.latency_ms} ms</span>
          )}
        </div>

        {isUser ? (
          <p className="text-sm leading-7 text-white whitespace-pre-wrap">{message.text}</p>
        ) : (
          <div className="prose prose-invert max-w-none text-sm leading-7 text-slate-100">
            <ReactMarkdown>{message.text}</ReactMarkdown>
          </div>
        )}

        {!isUser && message.sources?.length > 0 && (
          <div className="mt-5 border-t border-white/10 pt-4">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              <FileStack size={14} />
              Supporting sources
            </div>
            <div className="space-y-3">
              {message.sources.map((source) => (
                <div key={source.chunk_id || `${source.source_name}-${source.rank}`} className="rounded-2xl border border-white/10 bg-black/10 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-medium text-white">{source.source_name}</p>
                    <span className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-slate-300">
                      Page {source.page_number || 'n/a'}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-6 text-slate-400">{source.snippet}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

export default function ChatWindow({
  actualModel,
  composerFocusKey,
  hasKnowledgeBase,
  input,
  isLoading,
  kbStatus,
  messages,
  onSend,
  selectedModel,
  setInput,
  setSelectedModel,
}) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const previousMessageCountRef = useRef(messages.length);

  useEffect(() => {
    if (messages.length > previousMessageCountRef.current) {
      scrollRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' });
    }
    previousMessageCountRef.current = messages.length;
  }, [messages]);

  useEffect(() => {
    if (!hasKnowledgeBase) {
      return;
    }

    textareaRef.current?.focus();
    const valueLength = textareaRef.current?.value?.length || 0;
    textareaRef.current?.setSelectionRange(valueLength, valueLength);
  }, [composerFocusKey, hasKnowledgeBase]);

  return (
    <main className="flex min-h-screen flex-1 flex-col">
      <header className="border-b border-white/10 bg-[rgba(9,15,25,0.58)] px-5 py-5 backdrop-blur-xl lg:px-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-300/80">Search</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">Document questions</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
              Search indexed PDFs, review source citations, and keep the current model visible.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="metric-card">
              <div className="metric-label">
                <BrainCircuit size={15} />
                Active model
              </div>
              <p className="metric-value">{(actualModel || selectedModel).split('/').pop()}</p>
            </div>
            <div className="metric-card">
              <div className="metric-label">
                <FileStack size={15} />
                Documents
              </div>
              <p className="metric-value">{kbStatus.document_count || 0}</p>
            </div>
            <div className="metric-card">
              <div className="metric-label">
                <Clock3 size={15} />
                Chunks
              </div>
              <p className="metric-value">{kbStatus.chunk_count || 0}</p>
            </div>
          </div>
        </div>
      </header>

      <section className="flex flex-1 flex-col px-5 pb-6 pt-5 lg:px-8">
        <div className="mb-5 flex flex-col gap-4 rounded-[28px] border border-white/10 bg-white/[0.04] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Inference routing</p>
            <p className="mt-1 text-sm text-slate-300">Select the model tier you want the retrieval chain to use.</p>
          </div>

          <div className="relative">
            <button
              onClick={() => setIsMenuOpen((open) => !open)}
              className="flex min-w-[260px] items-center justify-between gap-3 rounded-2xl border border-white/10 bg-[rgba(10,19,30,0.72)] px-4 py-3 text-left text-sm text-white transition hover:border-cyan-400/30"
            >
              <div>
                <p className="font-medium">{FREE_MODELS.find((model) => model.id === selectedModel)?.name || 'Select model'}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {FREE_MODELS.find((model) => model.id === selectedModel)?.description}
                </p>
              </div>
              <ChevronDown size={16} className={`transition ${isMenuOpen ? 'rotate-180' : ''}`} />
            </button>

            {isMenuOpen && (
              <>
                <button
                  aria-label="Close model menu"
                  className="fixed inset-0 cursor-default bg-transparent"
                  onClick={() => setIsMenuOpen(false)}
                  type="button"
                />
                <div className="absolute right-0 z-20 mt-3 w-full rounded-3xl border border-white/10 bg-[rgba(8,13,22,0.97)] p-2 shadow-2xl shadow-cyan-950/30">
                  {FREE_MODELS.map((model) => (
                    <button
                      key={model.id}
                      className={`w-full rounded-2xl px-4 py-3 text-left transition ${
                        selectedModel === model.id ? 'bg-cyan-400/10 text-white' : 'text-slate-200 hover:bg-white/5'
                      }`}
                      onClick={() => {
                        setSelectedModel(model.id);
                        setIsMenuOpen(false);
                      }}
                    >
                      <p className="text-sm font-medium">{model.name}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-400">{model.description}</p>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="chat-surface">
          {!hasKnowledgeBase && (
            <div className="mb-5 rounded-[24px] border border-amber-300/20 bg-amber-300/10 px-5 py-4 text-sm leading-7 text-amber-50">
              No documents are indexed yet. Upload a PDF from the left panel to enable search and citations.
            </div>
          )}

          {messages.length === 0 && !isLoading ? (
            <div className="flex h-full flex-col items-center justify-center px-6 text-center">
              <div className="hero-icon">
                <MessageSquare size={28} />
              </div>
              <h3 className="mt-6 text-2xl font-semibold text-white">Ask about your documents</h3>
              <p className="mt-3 max-w-xl text-sm leading-7 text-slate-400">
                {hasKnowledgeBase
                  ? 'Summarize policies, compare reports, extract facts, or validate answers against indexed PDF evidence.'
                  : 'Start by uploading a PDF. After indexing completes, you can ask document questions here.'}
              </p>
            </div>
          ) : (
            <div className="chat-message-list space-y-5">
              {messages.map((message, index) => (
                <MessageCard key={`${message.role}-${index}`} message={message} />
              ))}
              {isLoading && (
                <div className="flex justify-start animate-rise">
                  <div className="message-card message-assistant">
                    <div className="flex items-center gap-3 text-sm text-slate-300">
                      <Loader2 className="animate-spin text-cyan-200" size={18} />
                      Retrieving relevant sections and preparing a response.
                    </div>
                  </div>
                </div>
              )}
              <div ref={scrollRef} />
            </div>
          )}
        </div>

        <div className="mt-5 rounded-[30px] border border-white/10 bg-[rgba(7,12,20,0.78)] p-3 shadow-[0_30px_80px_rgba(0,0,0,0.35)]">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
            <textarea
              className="min-h-[120px] flex-1 resize-none rounded-[24px] border border-white/10 bg-black/10 px-5 py-4 text-sm leading-7 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/30"
              ref={textareaRef}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  onSend();
                }
              }}
              placeholder="Ask a question about your indexed documents..."
              value={input}
            />

            <button
              className="flex h-[56px] items-center justify-center gap-2 rounded-[22px] bg-[linear-gradient(135deg,#34d399,#22d3ee)] px-6 text-sm font-semibold text-slate-950 transition hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-40"
              disabled={isLoading || !input.trim() || !hasKnowledgeBase}
              onClick={onSend}
            >
              {isLoading ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
              {hasKnowledgeBase ? 'Send' : 'Upload document first'}
            </button>
          </div>
          <p className="px-2 pt-3 text-xs text-slate-500">
            {hasKnowledgeBase
              ? 'Answers are generated from retrieved document chunks. If evidence is missing, the assistant should say so.'
              : 'Chat is disabled until at least one PDF is indexed into the knowledge base.'}
          </p>
        </div>
      </section>
    </main>
  );
}
