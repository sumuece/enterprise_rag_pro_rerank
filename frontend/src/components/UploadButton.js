import React, { useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, ChevronDown, Loader2, UploadCloud } from 'lucide-react';
import { EMBEDDING_MODELS } from '../models';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export default function UploadButton({
  activeEmbeddingModelId,
  embeddingModelId,
  onUploadSuccess,
  selectedEmbedding,
  setEmbeddingModelId,
}) {
  const inputRef = useRef(null);
  const [status, setStatus] = useState('idle');
  const [label, setLabel] = useState('Upload PDF knowledge pack');
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleFile = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    setStatus('uploading');
    setLabel(`Indexing ${file.name}`);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('embedding_model_id', embeddingModelId);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed.');
      }

      setStatus('success');
      setLabel(`${file.name} indexed successfully`);
      onUploadSuccess(data);
    } catch (error) {
      setStatus('error');
      setLabel(error.message || 'Upload failed');
    } finally {
      if (inputRef.current) {
        inputRef.current.value = '';
      }
      window.setTimeout(() => {
        setStatus('idle');
        setLabel('Upload PDF knowledge pack');
      }, 3500);
    }
  };

  return (
    <div className="space-y-3">
      <div className="rounded-3xl border border-white/10 bg-white/[0.03] px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">Embedding for next upload</p>
        <div className="relative mt-3">
          <button
            className="flex w-full items-center justify-between gap-3 rounded-2xl border border-white/10 bg-[rgba(10,19,30,0.72)] px-4 py-3 text-left text-sm text-white transition hover:border-cyan-400/30"
            onClick={() => setIsMenuOpen((open) => !open)}
            type="button"
          >
            <div>
              <p className="font-medium">{selectedEmbedding?.name || 'Select embedding model'}</p>
              <p className="mt-1 text-xs text-slate-400">{selectedEmbedding?.description}</p>
            </div>
            <ChevronDown size={16} className={`transition ${isMenuOpen ? 'rotate-180' : ''}`} />
          </button>

          {isMenuOpen && (
            <>
              <button
                aria-label="Close embedding menu"
                className="fixed inset-0 cursor-default bg-transparent"
                onClick={() => setIsMenuOpen(false)}
                type="button"
              />
              <div className="absolute right-0 z-20 mt-3 w-full rounded-3xl border border-white/10 bg-[rgba(8,13,22,0.97)] p-2 shadow-2xl shadow-cyan-950/30">
                {EMBEDDING_MODELS.map((model) => (
                  <button
                    key={model.id}
                    className={`w-full rounded-2xl px-4 py-3 text-left transition ${
                      embeddingModelId === model.id ? 'bg-cyan-400/10 text-white' : 'text-slate-200 hover:bg-white/5'
                    }`}
                    onClick={() => {
                      setEmbeddingModelId(model.id);
                      setIsMenuOpen(false);
                    }}
                    type="button"
                  >
                    <p className="text-sm font-medium">{model.name}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-400">{model.description}</p>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-400">
          {selectedEmbedding?.description}
        </p>
        {activeEmbeddingModelId && activeEmbeddingModelId !== embeddingModelId && (
          <p className="mt-2 text-xs leading-5 text-amber-200">
            Uploading with this selection will rebuild the index using a different embedding model.
          </p>
        )}
      </div>

      <label className={`upload-dropzone upload-${status}`}>
        <input
          ref={inputRef}
          accept=".pdf"
          className="hidden"
          onChange={handleFile}
          type="file"
        />

        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
            {status === 'uploading' && <Loader2 className="animate-spin text-cyan-200" size={18} />}
            {status === 'success' && <CheckCircle2 className="text-emerald-300" size={18} />}
            {status === 'error' && <AlertCircle className="text-rose-300" size={18} />}
            {status === 'idle' && <UploadCloud className="text-cyan-200" size={18} />}
          </div>
          <div>
            <p className="text-sm font-medium text-white">{label}</p>
            <p className="mt-1 text-xs text-slate-400">
              PDF only. Re-indexes the knowledge base with {selectedEmbedding?.name || 'the selected embedding model'}.
            </p>
          </div>
        </div>
      </label>
    </div>
  );
}
