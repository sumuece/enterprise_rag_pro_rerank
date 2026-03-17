# Enterprise RAG Pro

Enterprise RAG Pro is a document-question answering workspace for PDF corpora. It combines document ingestion, vector indexing, reranked retrieval, source-grounded answers, and a React UI for managing the knowledge base and model routing from one place.

## Highlights

- PDF-only ingestion with clean reindexing
- Source-grounded chat answers with citations and snippets
- Reranked retrieval using FlashRank before answer generation
- Separate chat-model and embedding-model selection
- OpenRouter support for free chat models and lower-cost embedding models
- Docker-based local development and production setups
- Empty-by-default startup with user-provided documents only

## Architecture

```text
+---------------------+          +------------------------+
| React Frontend      |  HTTP    | FastAPI Backend        |
| - chat workspace    +--------->+ - upload/chat/status   |
| - model selectors   |          | - document lifecycle   |
| - KB status         |          +-----------+------------+
+----------+----------+                      |
           |                                 |
           |                                 v
           |                      +------------------------+
           |                      | Ingestion Pipeline     |
           |                      | - PDF loading          |
           |                      | - chunking             |
           |                      | - metadata enrichment  |
           |                      | - embedding generation |
           |                      +-----------+------------+
           |                                  |
           |                                  v
           |                      +------------------------+
           |                      | Chroma Vector Store    |
           |                      | - active store dir     |
           |                      | - persisted on disk    |
           |                      +-----------+------------+
           |                                  |
           |                                  v
           |                      +------------------------+
           +--------------------->+ RAG Runtime            |
                                  | - retrieval            |
                                  | - FlashRank reranking  |
                                  | - LLM answer synthesis |
                                  +------------------------+
```

## Request Flow

### Upload and Index

1. A PDF is uploaded from the UI.
2. The backend stores the file in `backend/data/`.
3. The ingestion pipeline loads PDFs, splits them into chunks, and enriches each chunk with metadata such as page number, checksum, and source name.
4. Chunks are embedded using the selected embedding model.
5. A fresh Chroma store directory is created and persisted.
6. The active embedding model and active store directory are saved in `backend/chroma_db/embedding_config.json`.

### Ask a Question

1. The UI sends a prompt and selected chat model to `POST /chat`.
2. The backend opens the active Chroma store with the same embedding model that was used during indexing.
3. Retrieved chunks are reranked with FlashRank.
4. A prompt template is applied and the selected LLM generates the answer.
5. The API returns the answer, source snippets, and latency metrics.

## Repository Layout

```text
backend/
  main.py             FastAPI endpoints and KB state sync
  engine.py           Retrieval, reranking, model routing, answer generation
  ingest.py           PDF ingestion and vector-store rebuild flow
  model_registry.py   Embedding model registry and active-store metadata
  prompts.json        System prompt templates
  requirements.txt    Python dependencies

frontend/
  src/App.js          Shell state and top-level orchestration
  src/models.js       Chat and embedding model catalog
  src/components/
    ChatWindow.js     Main chat workspace and model controls
    Sidebar.js        KB summary and document inventory
    UploadButton.js   Embedding selection and upload trigger
  src/index.css       App styling
```

## Model Strategy

### Chat Models

The UI exposes OpenRouter-backed chat options for RAG answer generation, including a free-router option and multiple free model choices optimized for document QA.

### Embedding Models

The indexing pipeline supports a separate embedding model selection. This matters because retrieval quality and operational cost are driven by embeddings, not by the chat model.

Current embedding support includes:

- `google/models/gemini-embedding-001`
- `openrouter/openai/text-embedding-3-small`
- `openrouter/openai/text-embedding-3-large`
- `openrouter/qwen/qwen3-embedding-0.6b`

Note: model availability on OpenRouter can change over time. If a selected embedding model is not routable, indexing will fail and the active index embedding will remain unchanged.

## Why the Active Index Embedding Can Differ From the Selector

The UI intentionally distinguishes between:

- `Index embedding`: the embedding model used by the currently active stored index
- `Embedding for next upload`: the embedding model that will be used on the next reindex

Changing the dropdown alone does not rebuild the knowledge base. The active index only changes after a successful upload and reindex.

## Guardrails

The project includes runtime and product guardrails to keep retrieval quality, system behavior, and operator expectations aligned.

### Retrieval and Answering Guardrails

- Answers are generated from retrieved chunks rather than from the chat model alone.
- Retrieved chunks are reranked with FlashRank before final answer synthesis.
- Source snippets and citations are returned with answers so the UI can show evidence.
- The system is tuned for document-grounded QA, not for unrestricted open-domain chat.
- If no documents are indexed, chat is intentionally disabled and the UI prompts the user to upload content first.
- When the answer is not supported by indexed evidence, the assistant is expected to say so instead of guessing.

### Indexing Guardrails

- The embedding model used for retrieval is tied to the active stored index.
- Changing the embedding selector does not silently alter the live index; a successful reindex is required.
- Each reindex writes to a fresh Chroma store directory instead of mutating the active store in place.
- If an embedding provider fails during indexing, the previously active index remains unchanged.
- The backend records active embedding metadata so retrieval reopens the vector store with the correct embedding configuration.

### Model Routing Guardrails

- Chat-model selection and embedding-model selection are intentionally independent.
- Free or low-cost chat models can be used without forcing a change to the embedding pipeline.
- OpenRouter model availability is treated as dynamic; unsupported endpoints fail explicitly instead of degrading silently.
- The UI surfaces both the currently active index embedding and the next embedding selected for upload so state changes are visible.

### Content and Safety Guardrails

- The chat endpoint rejects requests that clearly ask for offensive cyber activity such as malware creation, credential theft, or exploit instructions.
- The chat endpoint rejects requests for violent wrongdoing such as weapons, explosives, or poisoning instructions.
- The chat endpoint rejects requests that indicate self-harm intent and routes the conversation away from operational guidance.
- The chat endpoint rejects requests to draft abusive, threatening, or harassing content.
- Prompt-injection style requests such as asking for hidden prompts, developer messages, or rule bypasses are explicitly refused.
- If indexed documents contain sensitive or risky material, the assistant is expected to stay at a policy, compliance, or defensive-summary level rather than converting that material into actionable harmful guidance.

### Operational Guardrails

- The knowledge base starts empty and only indexes user-provided PDFs.
- Status checks reconcile simple mismatches between source files and indexed content.
- Failed uploads do not overwrite the last working knowledge base state.
- Docker-friendly persistence keeps indexed data on disk across restarts when volumes are configured.

### Recommended Production Extensions

For a stricter production deployment, consider adding:

- file-size and page-count limits for uploads
- MIME-type and PDF structure validation before ingestion
- per-user or per-workspace isolation for documents and vector stores
- prompt-injection and malicious-document scanning before chunking
- document classification and quarantine flows for sensitive uploads
- configurable allowlists or denylists for regulated content domains
- rate limits on upload and chat endpoints
- audit logging for reindex events, model changes, and document deletion
- authentication and role-based access control around document lifecycle operations

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker Desktop for containerized development
- At least one API key:
  - `OPENROUTER_API_KEY` for OpenRouter chat or embeddings
  - `GOOGLE_API_KEY` for Gemini embeddings or Gemini chat fallback

### Environment Variables

Create or update `.env` in the repository root:

```env
GOOGLE_API_KEY=your_google_key
OPENROUTER_API_KEY=your_openrouter_key
```

## Local Run Without Docker

### Backend

```bash
cd backend
pip install -r requirements.txt
python ingest.py
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

Frontend: `http://localhost:3000`  
Backend: `http://localhost:8000`

## Docker Run

### Development

```bash
docker compose up --build
```

### Production

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### Convenience Scripts

PowerShell:

- `.\docker.ps1 dev-up`
- `.\docker.ps1 dev-build`
- `.\docker.ps1 dev-down`
- `.\docker.ps1 dev-logs`
- `.\docker.ps1 prod-up`
- `.\docker.ps1 prod-build`
- `.\docker.ps1 prod-down`
- `.\docker.ps1 prod-logs`

Command Prompt:

- `docker.bat dev-up`
- `docker.bat dev-build`
- `docker.bat dev-down`
- `docker.bat dev-logs`
- `docker.bat prod-up`
- `docker.bat prod-build`
- `docker.bat prod-down`
- `docker.bat prod-logs`

## API Surface

- `GET /health`
- `GET /documents`
- `GET /kb/status`
- `POST /upload`
- `DELETE /documents/{document_name}`
- `POST /chat`

## Operational Notes

### Clean Reindexing

Each ingestion run builds a fresh Chroma store directory and then marks it as active. This avoids in-place mutation of a live SQLite-backed Chroma store and reduces the risk of readonly-database errors inside Docker.

### Knowledge Base Reconciliation

On status and health checks, the backend reconciles simple mismatches between source PDFs on disk and indexed chunks. If documents exist without chunks, it triggers a rebuild. If chunks exist without source documents, it resets the knowledge base.

### Reranking

Retrieved chunks are passed through FlashRank before answer synthesis. This improves final context quality and helps the answer model focus on the most relevant evidence.

## Common Troubleshooting

### Gemini Quota Errors

If you hit `RESOURCE_EXHAUSTED` for Gemini embeddings, switch the embedding selector to an OpenRouter-backed embedding model and reindex.

### OpenRouter Endpoint Errors

If OpenRouter returns a `404` such as `No endpoints found for ...`, the model is not currently routable for your account or provider path. Choose another embedding or chat model and retry.

### Index Embedding Looks Wrong

If the top-level `Index embedding` card still shows an older model, the most recent reindex likely failed. The active index metadata only changes after a successful upload and rebuild.

## Documentation Notes

The backend modules now include function docstrings for ingestion, retrieval, API, and model registry workflows. Frontend orchestration points include succinct inline comments where behavior is not obvious, especially around upload/reindex flow and chat-state synchronization.
