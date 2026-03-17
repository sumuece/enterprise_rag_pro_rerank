"""Shared model registry utilities for embeddings and active Chroma store metadata."""

import json
import logging
import os
from pathlib import Path
from time import time

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings


load_dotenv()

logger = logging.getLogger("ModelRegistry")

BASE_DIR = Path(__file__).resolve().parent
DB_ROOT = BASE_DIR / "chroma_db"
EMBEDDING_CONFIG_PATH = DB_ROOT / "embedding_config.json"
DEFAULT_STORE_DIR = "store"

DEFAULT_EMBEDDING_MODEL = "google/models/gemini-embedding-001"
EMBEDDING_MODELS = {
    "google/models/gemini-embedding-001": {
        "provider": "google",
        "model_name": "models/gemini-embedding-001",
    },
    "openrouter/qwen/qwen3-embedding-0.6b": {
        "provider": "openrouter",
        "model_name": "qwen/qwen3-embedding-0.6b",
    },
    "openrouter/openai/text-embedding-3-small": {
        "provider": "openrouter",
        "model_name": "openai/text-embedding-3-small",
    },
    "openrouter/openai/text-embedding-3-large": {
        "provider": "openrouter",
        "model_name": "openai/text-embedding-3-large",
    },
}


def _normalize_embedding_model_id(model_id: str | None) -> str:
    """Return a supported embedding model ID or fall back to the default.

    Args:
        model_id: Candidate embedding model identifier from the UI or persisted config.

    Returns:
        A validated embedding model identifier present in ``EMBEDDING_MODELS``.
    """
    if model_id in EMBEDDING_MODELS:
        return model_id
    if model_id:
        logger.warning("Unsupported embedding model requested: %s. Falling back to default.", model_id)
    return DEFAULT_EMBEDDING_MODEL


def load_embedding_config() -> dict:
    """Load persisted embedding and store metadata for the active knowledge base.

    Returns:
        A dictionary containing the active embedding model ID and store directory,
        or an empty dictionary when no configuration has been persisted yet.
    """
    try:
        with EMBEDDING_CONFIG_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("Unable to read embedding config. %s", exc)
        return {}


def get_current_embedding_model_id() -> str:
    """Return the embedding model ID associated with the active index.

    Returns:
        The normalized embedding model ID for the currently active vector store.
    """
    config = load_embedding_config()
    return _normalize_embedding_model_id(config.get("embedding_model_id"))


def get_current_store_dir_name() -> str:
    """Return the Chroma store directory name for the active index.

    Returns:
        The directory name of the active Chroma store, or the default store name
        when no explicit store has been persisted.
    """
    config = load_embedding_config()
    store_dir = config.get("store_dir")
    return store_dir if isinstance(store_dir, str) and store_dir.strip() else DEFAULT_STORE_DIR


def get_current_store_path() -> Path:
    """Resolve the absolute path of the active Chroma store directory.

    Returns:
        The filesystem path of the Chroma store currently treated as active.
    """
    return DB_ROOT / get_current_store_dir_name()


def build_new_store_dir_name() -> str:
    """Generate a unique Chroma store directory name for a fresh index build.

    Returns:
        A timestamp-based directory name suitable for a newly built Chroma store.
    """
    return f"store_{int(time() * 1000)}"


def save_embedding_config(model_id: str, store_dir: str | None = None) -> None:
    """Persist the embedding model and active Chroma store directory.

    Args:
        model_id: Embedding model identifier to persist as the active index model.
        store_dir: Optional Chroma store directory name to persist as active.
    """
    normalized_id = _normalize_embedding_model_id(model_id)
    DB_ROOT.mkdir(parents=True, exist_ok=True)
    with EMBEDDING_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "embedding_model_id": normalized_id,
                "store_dir": store_dir or get_current_store_dir_name(),
            },
            handle,
            indent=2,
        )


def build_embeddings(model_id: str | None = None):
    """Instantiate the embedding client for the requested or active embedding model.

    Args:
        model_id: Optional embedding model identifier to instantiate immediately.

    Returns:
        A tuple of ``(embedding_client, resolved_model_id)`` for the selected model.
    """
    resolved_id = _normalize_embedding_model_id(model_id or get_current_embedding_model_id())
    config = EMBEDDING_MODELS[resolved_id]

    if config["provider"] == "google":
        return (
            GoogleGenerativeAIEmbeddings(
                model=config["model_name"],
                api_key=os.getenv("GOOGLE_API_KEY"),
            ),
            resolved_id,
        )

    return (
        OpenAIEmbeddings(
            model=config["model_name"],
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers={
                "HTTP-Referer": "https://localhost",
                "X-Title": "Enterprise RAG Pro",
            },
        ),
        resolved_id,
    )
