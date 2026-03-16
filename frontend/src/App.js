import React, { useEffect, useState } from 'react';
import ChatWindow from './components/ChatWindow';
import Sidebar from './components/Sidebar';
import { FREE_MODELS } from './models';

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState(FREE_MODELS[0].id);
  const [actualModel, setActualModel] = useState(null);
  const [composerFocusKey, setComposerFocusKey] = useState(0);
  const [kbStatus, setKbStatus] = useState({
    status: 'loading',
    chunk_count: 0,
    document_count: 0,
    documents: [],
  });
  const hasKnowledgeBase = kbStatus.status === 'ready' && (kbStatus.document_count || 0) > 0;

  const refreshKnowledgeBase = async () => {
    try {
      const response = await fetch(`${API_BASE}/kb/status`);
      const data = await response.json();
      setKbStatus(data);
    } catch (error) {
      setKbStatus((previous) => ({
        ...previous,
        status: 'offline',
      }));
    }
  };

  useEffect(() => {
    refreshKnowledgeBase();
  }, []);

  const handleSend = async () => {
    const prompt = input.trim();
    if (!prompt || isLoading) {
      return;
    }

    if (!hasKnowledgeBase) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          text: 'Upload at least one PDF before starting chat. Once a document is indexed, answers will include supporting citations when available.',
          error: true,
          sources: [],
        },
      ]);
      return;
    }

    const userMessage = { role: 'user', text: prompt };
    setMessages((previous) => [...previous, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, model_id: selectedModel }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to generate a response.');
      }

      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          text: data.answer,
          sources: data.sources || [],
          metrics: data.metrics || null,
          actualModel: data.actual_model,
        },
      ]);
      setActualModel(data.actual_model);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          text: error.message || 'Error connecting to server.',
          error: true,
          sources: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setActualModel(null);
  };

  const handleUploadSuccess = (payload) => {
    const primaryDocument = payload.documents?.[0]?.name || payload.message.replace('Successfully indexed ', '');
    setMessages((previous) => [
      ...previous,
      {
        role: 'assistant',
        text: `Indexed ${payload.message.replace('Successfully indexed ', '')}. The knowledge base now contains ${payload.document_count} document(s) across ${payload.chunk_count} retrieval chunks.`,
        sources: [],
      },
    ]);
    setInput(payload.suggested_prompt || `Give me an executive summary of ${primaryDocument}.`);
    setComposerFocusKey((value) => value + 1);
    refreshKnowledgeBase();
  };

  const handleDeleteDocument = async (documentName) => {
    try {
      const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(documentName)}`, {
        method: 'DELETE',
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to delete document.');
      }

      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          text: `${data.deleted_document} was removed from the knowledge base. ${data.document_count} document(s) remain indexed.`,
          sources: [],
        },
      ]);

      if (!data.document_count) {
        setInput('');
        setActualModel(null);
      }

      refreshKnowledgeBase();
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          text: error.message || 'Failed to delete document.',
          error: true,
          sources: [],
        },
      ]);
    }
  };

  return (
    <div className="app-shell">
      <div className="app-backdrop" />
      <Sidebar
        documents={kbStatus.documents || []}
        kbStatus={kbStatus}
        onDeleteDocument={handleDeleteDocument}
        onNewChat={handleNewChat}
        onRefresh={refreshKnowledgeBase}
        onUploadSuccess={handleUploadSuccess}
      />
      <ChatWindow
        actualModel={actualModel}
        composerFocusKey={composerFocusKey}
        hasKnowledgeBase={hasKnowledgeBase}
        input={input}
        isLoading={isLoading}
        kbStatus={kbStatus}
        messages={messages}
        onSend={handleSend}
        selectedModel={selectedModel}
        setInput={setInput}
        setSelectedModel={setSelectedModel}
      />
    </div>
  );
}

export default App;
