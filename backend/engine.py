import json
import logging
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import FlashrankRerank


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("RAG-Engine")

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chroma_db"
PROMPTS_PATH = BASE_DIR / "prompts.json"
COLLECTION_NAME = "enterprise_rag_documents"
DEFAULT_MODEL = "openrouter/google/gemini-2.0-flash-001"
FALLBACK_MODELS = [
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct:free",
]


def load_system_prompt(key="rag_system_prompt"):
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


def _get_embeddings():
    logger.info("Initializing embeddings model.")
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def get_vectorstore():
    if not DB_PATH.exists():
        raise RuntimeError("Knowledge base is empty. Upload and index at least one PDF first.")

    logger.info("Opening vector store at %s", DB_PATH)
    return Chroma(
        persist_directory=str(DB_PATH),
        embedding_function=_get_embeddings(),
        collection_name=COLLECTION_NAME,
    )


def get_collection_stats():
    if not DB_PATH.exists():
        logger.info("Collection stats requested while knowledge base is empty.")
        return {"chunk_count": 0, "status": "empty"}

    try:
        vectorstore = get_vectorstore()
        count = vectorstore._collection.count()
        logger.info("Collection stats loaded. chunks=%s", count)
        return {"chunk_count": count, "status": "ready" if count else "empty"}
    except Exception as exc:
        logger.error("Failed to read collection stats: %s", exc)
        return {"chunk_count": 0, "status": "error"}


def get_llm(model_id: str):
    requested_id = model_id or DEFAULT_MODEL
    is_openrouter = requested_id.startswith("openrouter/")
    cleaned_model = requested_id.replace("openrouter/", "") if is_openrouter else requested_id

    priority_list = [cleaned_model]
    for fallback in FALLBACK_MODELS:
        if fallback not in priority_list:
            priority_list.append(fallback)

    last_error = None
    for model_name in priority_list:
        try:
            logger.info("Initializing LLM candidate: %s", model_name)
            if is_openrouter:
                provider = "openai"
                base_url = "https://openrouter.ai/api/v1"
                api_key = os.getenv("OPENROUTER_API_KEY")
            else:
                provider = "google_genai"
                base_url = None
                api_key = os.getenv("GOOGLE_API_KEY")

            llm = init_chat_model(
                model_name,
                model_provider=provider,
                base_url=base_url,
                api_key=api_key,
                temperature=0.1,
                streaming=False,
                default_headers={
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "Enterprise RAG Pro",
                },
            )
            return llm, model_name
        except Exception as exc:
            last_error = exc
            logger.error("Model initialization failed for %s: %s", model_name, exc)

    raise RuntimeError(f"All model initializations failed: {last_error}")


def build_sources(documents):
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
