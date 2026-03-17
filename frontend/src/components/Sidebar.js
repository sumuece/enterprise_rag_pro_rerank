import React from 'react';
import { Database, FileText, Plus, RefreshCw, ShieldCheck, X } from 'lucide-react';

function formatFileSize(sizeBytes) {
  if (!sizeBytes) {
    return '0 KB';
  }
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = sizeBytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

export default function Sidebar({
  documents,
  kbStatus,
  onDeleteDocument,
  onNewChat,
  onRefresh,
}) {
  const statusTone =
    kbStatus.status === 'ready'
      ? 'emerald'
      : kbStatus.status === 'offline'
        ? 'amber'
        : kbStatus.status === 'error'
          ? 'rose'
          : 'slate';

  return (
    <aside className="w-full max-w-[340px] border-r border-white/10 bg-[rgba(7,12,20,0.78)] backdrop-blur-xl lg:h-screen lg:min-h-0 lg:overflow-hidden">
      <div className="flex h-full min-h-0 flex-col">
        <div className="border-b border-white/10 p-6">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-300/80">Documents</p>
              <h1 className="mt-2 text-2xl font-semibold text-white">Knowledge Base</h1>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                Manage documents, indexing status, and source coverage from one workspace.
              </p>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-200">
              <ShieldCheck size={20} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={onNewChat}
              className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10"
            >
              <Plus size={16} />
              New chat
            </button>
            <button
              onClick={onRefresh}
              className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-transparent px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-cyan-400/30 hover:bg-cyan-400/10"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>

          <div className={`status-card status-${statusTone}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Database size={16} />
                <span className="text-sm font-medium">Knowledge base</span>
              </div>
              <span className="status-pill">{kbStatus.status}</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-slate-400">Documents</p>
                <p className="mt-1 text-xl font-semibold text-white">{kbStatus.document_count || 0}</p>
              </div>
              <div>
                <p className="text-slate-400">Chunks</p>
                <p className="mt-1 text-xl font-semibold text-white">{kbStatus.chunk_count || 0}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Documents</p>
            <span className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-slate-300">
              {documents.length} loaded
            </span>
          </div>

          {documents.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.03] p-5 text-sm leading-6 text-slate-400">
              Upload PDF reports, policies, SOPs, or knowledge manuals to initialize the retrieval layer.
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((document) => (
                <div key={document.name} className="rounded-3xl border border-white/10 bg-white/[0.04] p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-2xl bg-white/10 text-cyan-200">
                      <FileText size={16} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-white">{document.name}</p>
                      <p className="mt-1 text-xs text-slate-400">{formatFileSize(document.size_bytes)}</p>
                    </div>
                    <button
                      aria-label={`Delete ${document.name}`}
                      className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 text-slate-400 transition hover:border-rose-400/40 hover:bg-rose-400/10 hover:text-rose-200"
                      onClick={() => onDeleteDocument(document.name)}
                      type="button"
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
