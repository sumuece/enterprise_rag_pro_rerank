import logging
import shutil
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine import answer_query, get_collection_stats
from ingest import DATA_PATH, reset_knowledge_base, run_ingestion
from model_registry import DEFAULT_EMBEDDING_MODEL, get_current_embedding_model_id


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG-API")

app = FastAPI(title="Enterprise RAG Pro API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=8000)
    model_id: str = "openrouter/free"


def _list_documents():
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    documents = []
    for file_path in sorted(DATA_PATH.glob("*.pdf")):
        documents.append(
            {
                "name": file_path.name,
                "path": str(file_path),
                "size_bytes": file_path.stat().st_size,
                "updated_at": file_path.stat().st_mtime,
            }
        )
    logger.info("Listed %s document(s) from the data directory.", len(documents))
    return documents


def _sync_knowledge_base_state():
    documents = _list_documents()
    stats = get_collection_stats()
    has_documents = bool(documents)
    has_chunks = stats["chunk_count"] > 0
    embedding_model_id = stats.get("embedding_model_id") or get_current_embedding_model_id()

    if has_documents and not has_chunks:
        logger.warning(
            "Knowledge base mismatch detected: %s document(s) on disk but no indexed chunks. Rebuilding index.",
            len(documents),
        )
        ingestion_result = run_ingestion()
        return {
            "status": ingestion_result["status"],
            "chunk_count": ingestion_result["chunk_count"],
            "document_count": ingestion_result["document_count"],
            "documents": ingestion_result["documents"],
            "embedding_model_id": ingestion_result["embedding_model_id"],
        }

    if not has_documents and has_chunks:
        logger.warning("Knowledge base mismatch detected: indexed chunks exist without source PDFs. Resetting index.")
        reset_knowledge_base()
        return {
            "status": "empty",
            "chunk_count": 0,
            "document_count": 0,
            "documents": [],
            "embedding_model_id": get_current_embedding_model_id(),
        }

    return {
        "status": stats["status"],
        "chunk_count": stats["chunk_count"],
        "document_count": len(documents),
        "documents": documents,
        "embedding_model_id": embedding_model_id,
    }


@app.get("/health")
async def health_check():
    kb_state = _sync_knowledge_base_state()
    logger.info("Health check requested. kb_status=%s chunk_count=%s", kb_state["status"], kb_state["chunk_count"])
    return {
        "status": "ok",
        "knowledge_base": kb_state["status"],
        "chunk_count": kb_state["chunk_count"],
        "document_count": kb_state["document_count"],
        "embedding_model_id": kb_state["embedding_model_id"],
    }


@app.get("/documents")
async def list_documents():
    logger.info("Document list endpoint requested.")
    kb_state = _sync_knowledge_base_state()
    return {"documents": kb_state["documents"]}


@app.get("/kb/status")
async def knowledge_base_status():
    kb_state = _sync_knowledge_base_state()
    logger.info(
        "Knowledge base status requested. status=%s chunk_count=%s",
        kb_state["status"],
        kb_state["chunk_count"],
    )
    return {
        "status": kb_state["status"],
        "chunk_count": kb_state["chunk_count"],
        "document_count": kb_state["document_count"],
        "documents": kb_state["documents"],
        "embedding_model_id": kb_state["embedding_model_id"],
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    embedding_model_id: str = Form(DEFAULT_EMBEDDING_MODEL),
):
    logger.info("Received upload request: %s embedding_model=%s", file.filename, embedding_model_id)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename).name
        save_path = DATA_PATH / safe_name

        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info("Saved upload to %s", save_path)
        ingestion_result = run_ingestion(embedding_model_id)
        logger.info(
            "Upload indexed successfully. file=%s documents=%s chunks=%s embedding_model=%s",
            safe_name,
            ingestion_result["document_count"],
            ingestion_result["chunk_count"],
            ingestion_result["embedding_model_id"],
        )
        return {
            "message": f"Successfully indexed {safe_name}",
            "status": ingestion_result["status"],
            "document_count": ingestion_result["document_count"],
            "chunk_count": ingestion_result["chunk_count"],
            "documents": ingestion_result["documents"],
            "embedding_model_id": ingestion_result["embedding_model_id"],
            "suggested_prompt": next(
                (
                    document.get("suggested_prompt")
                    for document in ingestion_result["documents"]
                    if document.get("name") == safe_name
                ),
                None,
            ),
        }
    except Exception as exc:
        logger.exception("Upload/Index failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process document.") from exc


@app.delete("/documents/{document_name:path}")
async def delete_document(document_name: str):
    safe_name = Path(unquote(document_name)).name
    target_path = DATA_PATH / safe_name
    logger.info("Delete document requested for %s", safe_name)

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        target_path.unlink()
        logger.info("Deleted source file %s", target_path)
        remaining_documents = list(DATA_PATH.glob("*.pdf"))
        ingestion_result = run_ingestion() if remaining_documents else reset_knowledge_base()
        logger.info(
            "Delete completed. deleted=%s remaining_documents=%s remaining_chunks=%s",
            safe_name,
            ingestion_result["document_count"],
            ingestion_result["chunk_count"],
        )
        return {
            "message": f"Deleted {safe_name}",
            "deleted_document": safe_name,
            "status": ingestion_result["status"],
            "document_count": ingestion_result["document_count"],
            "chunk_count": ingestion_result["chunk_count"],
            "documents": ingestion_result["documents"],
            "embedding_model_id": ingestion_result["embedding_model_id"],
        }
    except Exception as exc:
        logger.exception("Delete failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete document.") from exc


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    logger.info("Chat request received for model: %s", request.model_id)
    try:
        _sync_knowledge_base_state()
        result = answer_query(request.prompt, request.model_id)
        logger.info(
            "Chat request completed. model=%s retrieved_chunks=%s latency_ms=%s",
            result["actual_model"],
            result["metrics"]["retrieved_chunks"],
            result["metrics"]["latency_ms"],
        )
        return result
    except RuntimeError as exc:
        logger.error("Chat blocked: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chat failed: %s", exc)
        raise HTTPException(status_code=500, detail="Response generation failed.") from exc
