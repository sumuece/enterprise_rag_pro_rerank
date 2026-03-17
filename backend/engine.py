"""RAG runtime utilities for retrieval, reranking, model selection, and answer generation."""

import json
import logging
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import FlashrankRerank

from model_registry import build_embeddings, get_current_embedding_model_id, get_current_store_path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("RAG-Engine")

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_PATH = BASE_DIR / "prompts.json"
COLLECTION_NAME = "enterprise_rag_documents"
DEFAULT_MODEL = "openrouter/free"
OPENROUTER_FALLBACK_MODELS = [
    "openrouter/stepfun/step-3.5-flash:free",
    "openrouter/qwen/qwen3-next-80b-a3b-instruct:free",
    "openrouter/arcee-ai/trinity-large-preview:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
]
GOOGLE_FALLBACK_MODELS = ["google/gemini-2.0-flash-001"]


def load_system_prompt(key="rag_system_prompt"):
    """Load a named prompt template from disk with a safe in-code fallback.

    Args:
        key: Prompt key to read from ``prompts.json``.

    Returns:
        The resolved prompt template string.
    """
    try:
        with PROMPTS_PATH.open("r", encoding="utf-8") as handle:
            prompts = json.load(handle)
        return prompts[key]["template"]
    except Exception as exc:
        logger.warning("Unable to load prompts.json, using fallback prompt. %s", exc)
        return (
            "You are an enterprise retrieval assistant. Answer only from the context.\n"
            "If the answer is missing, clearly say you do not know.\n\n"
            "Context:\n{context}"
        )


def get_vectorstore():
    """Open the active Chroma store with the embedding model used to build it.

    Returns:
        A ``Chroma`` vector store bound to the active index path and embedding model.
    """
    db_path = get_current_store_path()
    if not db_path.exists():
        raise RuntimeError("Knowledge base is empty. Upload and index at least one PDF first.")

    embeddings, embedding_model_id = build_embeddings()
    logger.info("Opening vector store at %s with embedding model %s", db_path, embedding_model_id)
    return Chroma(
        persist_directory=str(db_path),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )


def get_collection_stats():
    """Return the current index health and chunk count for UI status endpoints.

    Returns:
        A dictionary containing chunk count, readiness state, and active embedding model ID.
    """
    if not get_current_store_path().exists():
        logger.info("Collection stats requested while knowledge base is empty.")
        return {
            "chunk_count": 0,
            "status": "empty",
            "embedding_model_id": get_current_embedding_model_id(),
        }

    try:
        vectorstore = get_vectorstore()
        count = vectorstore._collection.count()
        logger.info("Collection stats loaded. chunks=%s", count)
        return {
            "chunk_count": count,
            "status": "ready" if count else "empty",
            "embedding_model_id": get_current_embedding_model_id(),
        }
    except Exception as exc:
        logger.error("Failed to read collection stats: %s", exc)
        return {
            "chunk_count": 0,
            "status": "error",
            "embedding_model_id": get_current_embedding_model_id(),
        }


def _is_openrouter_model(model_id: str):
    """Determine whether a model ID should be routed through OpenRouter.

    Args:
        model_id: Chat model identifier supplied by the UI or fallback logic.

    Returns:
        ``True`` when the model should be initialized through the OpenRouter endpoint.
    """
    return model_id == "openrouter/free" or model_id.startswith("openrouter/") or model_id.endswith(":free")


def _resolve_model_config(model_id: str):
    """Map a model ID to the provider configuration expected by LangChain.

    Args:
        model_id: Chat model identifier to resolve.

    Returns:
        A provider configuration dictionary for ``init_chat_model``.
    """
    if _is_openrouter_model(model_id):
        if model_id == "openrouter/free":
            resolved_model = model_id
        elif model_id.startswith("openrouter/"):
            resolved_model = model_id.replace("openrouter/", "", 1)
        else:
            resolved_model = model_id

        return {
            "provider": "openai",
            "model_name": resolved_model,
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPENROUTER_API_KEY"),
        }

    return {
        "provider": "google_genai",
        "model_name": model_id,
        "base_url": None,
        "api_key": os.getenv("GOOGLE_API_KEY"),
    }


def get_llm(model_id: str):
    """Create the chat model client with provider-aware fallback behavior.

    Args:
        model_id: Preferred chat model identifier requested by the user.

    Returns:
        A tuple of ``(llm, active_model_name)`` for the first successfully initialized model.
    """
    requested_id = model_id or DEFAULT_MODEL
    fallback_models = OPENROUTER_FALLBACK_MODELS if _is_openrouter_model(requested_id) else GOOGLE_FALLBACK_MODELS

    priority_list = [requested_id]
    for fallback in fallback_models:
        if fallback not in priority_list:
            priority_list.append(fallback)

    last_error = None
    for candidate in priority_list:
        try:
            config = _resolve_model_config(candidate)
            logger.info("Initializing LLM candidate: %s", config["model_name"])

            llm = init_chat_model(
                config["model_name"],
                model_provider=config["provider"],
                base_url=config["base_url"],
                api_key=config["api_key"],
                temperature=0.1,
                streaming=False,
                default_headers={
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "Enterprise RAG Pro",
                },
            )
            return llm, config["model_name"]
        except Exception as exc:
            last_error = exc
            logger.error("Model initialization failed for %s: %s", candidate, exc)

    raise RuntimeError(f"All model initializations failed: {last_error}")


def build_sources(documents):
    """Convert retrieved LangChain documents into a compact UI-friendly source payload.

    Args:
        documents: Retrieved LangChain documents returned by the RAG chain.

    Returns:
        A list of compact source dictionaries for UI rendering.
    """
    logger.info("Building source payload for %s retrieved chunks.", len(documents))
    sources = []
    for rank, doc in enumerate(documents, start=1):
        metadata = doc.metadata or {}
        snippet = " ".join(doc.page_content.split())
        sources.append(
            {
                "rank": rank,
                "source": metadata.get("source"),
                "source_name": metadata.get("source_name") or Path(metadata.get("source", "Unknown")).name,
                "page_number": metadata.get("page_number") or metadata.get("page"),
                "chunk_id": metadata.get("chunk_id"),
                "checksum": metadata.get("checksum"),
                "snippet": snippet[:320],
            }
        )
    return sources


def get_rag_chain(model_id: str):
    """Assemble the retrieval, reranking, and answer-generation chain for a request.

    Args:
        model_id: Preferred chat model identifier for the request.

    Returns:
        A tuple of ``(retrieval_chain, active_model_name)``.
    """
    logger.info("Building RAG chain for request: %s", model_id)
    vectorstore = get_vectorstore()
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": 12})
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=FlashrankRerank(top_n=5),
        base_retriever=base_retriever,
    )

    llm, active_model = get_llm(model_id)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_system_prompt()),
            ("human", "{input}"),
        ]
    )
    answer_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(compression_retriever, answer_chain)
    logger.info("RAG chain ready for model %s", active_model)
    return retrieval_chain, active_model


def answer_query(prompt: str, model_id: str):
    """Run the end-to-end RAG flow and return answer, sources, and latency metrics.

    Args:
        prompt: User question to answer against the indexed documents.
        model_id: Preferred chat model identifier for the request.

    Returns:
        A dictionary containing the answer text, active model, sources, and metrics.
    """
    logger.info("Answer generation started. prompt_length=%s model=%s", len(prompt), model_id)
    started_at = perf_counter()
    chain, active_model = get_rag_chain(model_id)
    response = chain.invoke({"input": prompt})
    context_docs = response.get("context", [])
    elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
    logger.info(
        "Answer generation completed. model=%s latency_ms=%s retrieved_chunks=%s",
        active_model,
        elapsed_ms,
        len(context_docs),
    )

    return {
        "answer": response["answer"],
        "actual_model": active_model,
        "sources": build_sources(context_docs),
        "metrics": {
            "latency_ms": elapsed_ms,
            "retrieved_chunks": len(context_docs),
        },
    }
