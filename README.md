# Document Search App

PDF document search app with:

- clean re-indexing for uploaded documents
- reranked retrieval with source snippets and page citations
- knowledge-base health and inventory endpoints
- React UI for document management and chat
- empty-by-default Docker startup with user-uploaded documents only

## Backend

1. Add `GOOGLE_API_KEY` and/or `OPENROUTER_API_KEY` to `.env`
2. The chat UI now defaults to `openrouter/free` and includes several current zero-cost OpenRouter models suited to RAG-style document QA
3. The sidebar upload flow includes an embedding-model selector, and the backend reuses the same embedding model for retrieval as the one used during indexing
4. Upload PDFs from the UI, or place them in `backend/data/` before running manual ingestion
5. Run `python backend/ingest.py` to build the vector store
6. Run `uvicorn main:app --reload` inside `backend/`

## Frontend

1. Install dependencies in `frontend/`
2. Optionally set `REACT_APP_API_BASE_URL`
3. Run `npm start`

## Docker behavior

- `docker compose up` now runs in development mode with live reload
- Backend changes are picked up automatically through `uvicorn --reload`
- Frontend changes are picked up automatically through the React dev server
- Containers start with an empty knowledge base
- User uploads are stored in Docker volumes instead of bundled sample files
- If no documents have been uploaded yet, chat returns a controlled "knowledge base is empty" message

## Docker modes

- Development: `docker compose up --build`
- Production: `docker compose -f docker-compose.prod.yml up --build -d`
- Development uses bind mounts and hot reload
- Production uses the Docker `production` stages and serves the frontend on port `80`

## PowerShell shortcuts

- `.\docker.ps1 dev-up`
- `.\docker.ps1 dev-build`
- `.\docker.ps1 dev-down`
- `.\docker.ps1 dev-logs`
- `.\docker.ps1 prod-up`
- `.\docker.ps1 prod-build`
- `.\docker.ps1 prod-down`
- `.\docker.ps1 prod-logs`

## Command Prompt shortcuts

- `docker.bat dev-up`
- `docker.bat dev-build`
- `docker.bat dev-down`
- `docker.bat dev-logs`
- `docker.bat prod-up`
- `docker.bat prod-build`
- `docker.bat prod-down`
- `docker.bat prod-logs`

## Docker dev ports

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`

## Docker production ports

- Frontend: `http://localhost`
- Backend API: `http://localhost:8000`

## API endpoints

- `GET /health`
- `GET /documents`
- `GET /kb/status`
- `POST /upload`
- `POST /chat`

## Repo hygiene

- Local environment files, Python virtualenvs, Chroma data, uploaded PDFs, frontend builds, and `node_modules` are ignored by Git
- Docker build contexts exclude backend virtualenv/cache data and frontend dependency/build artifacts
