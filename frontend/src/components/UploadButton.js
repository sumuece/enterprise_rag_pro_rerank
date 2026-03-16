import React, { useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Loader2, UploadCloud } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export default function UploadButton({ onUploadSuccess }) {
  const inputRef = useRef(null);
  const [status, setStatus] = useState('idle');
  const [label, setLabel] = useState('Upload PDF knowledge pack');

  const handleFile = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    setStatus('uploading');
    setLabel(`Indexing ${file.name}`);

    const formData = new FormData();
    formData.append('file', file);

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
          <p className="mt-1 text-xs text-slate-400">PDF only. Re-indexes the knowledge base to keep retrieval clean.</p>
        </div>
      </div>
    </label>
  );
}
