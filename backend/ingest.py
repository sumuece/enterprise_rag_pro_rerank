import hashlib
import logging
import shutil
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Ingestor")

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data"
DB_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "enterprise_rag_documents"
CHUNK_SIZE = 1100
CHUNK_OVERLAP = 180


def _get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def _build_suggested_prompt(document_name: str, sample_text: str) -> str:
    safe_name = document_name or "this document"
    corpus = f"{safe_name} {sample_text}".lower()

    if any(keyword in corpus for keyword in ["policy", "compliance", "governance", "security", "privacy", "procedure", "sop", "control"]):
        return (
            f"Summarize {safe_name} for leadership, including the main policies, compliance obligations, "
            "operational responsibilities, and any important risks or enforcement points."
        )

    if any(keyword in corpus for keyword in ["report", "quarter", "annual", "review", "board", "finance", "financial", "revenue", "forecast", "earnings"]):
        return (
            f"Give me an executive briefing on {safe_name}, covering the main findings, performance trends, "
            "financial or operational highlights, and the key risks or follow-up actions."
        )

    if any(keyword in corpus for keyword in ["manual", "guide", "playbook", "runbook", "architecture", "design", "technical", "spec", "api", "system", "deployment"]):
        return (
            f"Explain {safe_name} as a technical briefing, including the main components, workflows, "
            "implementation details, dependencies, and any operational constraints or risks."
        )

    if any(keyword in corpus for keyword in ["contract", "agreement", "msa", "sow", "legal", "terms", "liability", "termination", "payment"]):
        return (
            f"Review {safe_name} and extract the key commercial terms, obligations, timelines, "
            "renewal or termination clauses, and any legal or operational risks I should pay attention to."
        )

    return (
        f"Give me an executive summary of {safe_name}, including the main topics, key findings, "
        "and any important risks or action items."
    )


def _compute_checksum(file_path: Path) -> str:
    logger.info("Computing checksum for %s", file_path.name)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clear_directory(directory: Path) -> None:
    if not directory.exists():
        return

    logger.info("Clearing directory contents: %s", directory)
    for item in directory.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def reset_knowledge_base():
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    DB_PATH.mkdir(parents=True, exist_ok=True)
    _clear_directory(DB_PATH)
    logger.info("Knowledge base reset. No indexed documents remain.")
    return {
        "documents": [],
        "document_count": 0,
        "chunk_count": 0,
        "status": "empty",
    }


def _prepare_chunks():
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    logger.info("Scanning directory: %s", DATA_PATH)

    loader = DirectoryLoader(str(DATA_PATH), glob="*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()
    if not docs:
        logger.warning("No PDF documents found in %s. Ingestion skipped.", DATA_PATH)
        return [], []

    logger.info("Loaded %s raw document pages.", len(docs))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info("Split raw documents into %s chunks.", len(chunks))

    file_summaries = {}
    checksum_cache = {}
    sample_text_by_source = {}
    for index, chunk in enumerate(chunks):
        source_path = Path(chunk.metadata.get("source", "unknown"))
        if source_path.exists():
            checksum = checksum_cache.setdefault(source_path, _compute_checksum(source_path))
        else:
            checksum = "unknown"
        page_number = int(chunk.metadata.get("page", 0)) + 1
        source_name = source_path.name
        chunk_id = f"{source_name}:{page_number}:{index}"

        chunk.metadata.update(
            {
                "source": str(source_path),
                "source_name": source_name,
                "page_number": page_number,
                "checksum": checksum,
                "chunk_id": chunk_id,
            }
        )

        summary = file_summaries.setdefault(
            source_name,
            {
                "name": source_name,
                "path": str(source_path),
                "pages": 0,
                "chunks": 0,
                "checksum": checksum,
                "size_bytes": source_path.stat().st_size if source_path.exists() else 0,
            },
        )
        summary["pages"] = max(summary["pages"], page_number)
        summary["chunks"] += 1
        sample_text_by_source.setdefault(source_name, " ".join(chunk.page_content.split())[:1200])

    for source_name, summary in file_summaries.items():
        summary["suggested_prompt"] = _build_suggested_prompt(
            source_name,
            sample_text_by_source.get(source_name, ""),
        )
        logger.info(
            "Prepared summary for %s pages=%s chunks=%s",
            source_name,
            summary["pages"],
            summary["chunks"],
        )

    logger.info("Loaded %s pages and created %s chunks.", len(docs), len(chunks))
    return chunks, sorted(file_summaries.values(), key=lambda item: item["name"].lower())


def run_ingestion():
    logger.info("--- Starting enterprise ingestion ---")
    chunks, documents = _prepare_chunks()
    if not chunks:
        return reset_knowledge_base()

    if DB_PATH.exists():
        logger.info("Resetting existing Chroma contents for clean re-indexing.")
        _clear_directory(DB_PATH)
    else:
        DB_PATH.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=_get_embeddings(),
        persist_directory=str(DB_PATH),
        collection_name=COLLECTION_NAME,
    )
    if hasattr(vectorstore, "persist"):
        vectorstore.persist()
        logger.info("Vector store persisted to %s", DB_PATH)

    logger.info(
        "Ingestion complete. Indexed %s documents and %s chunks.",
        len(documents),
        len(chunks),
    )
    return {
        "documents": documents,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "status": "ready",
    }


if __name__ == "__main__":
    run_ingestion()
