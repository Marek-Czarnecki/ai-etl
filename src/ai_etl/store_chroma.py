"""ChromaDB persistence for run artifacts."""

from __future__ import annotations

import logging
from typing import Dict, Optional
from urllib.parse import urlparse

import chromadb

from ai_etl.llm_ollama import OllamaClient

logger = logging.getLogger(__name__)


def _parse_chroma_url(chroma_url: str) -> tuple[str, int, bool]:
    parsed = urlparse(chroma_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    ssl = parsed.scheme == "https"
    return host, port, ssl


def store_run(
    chroma_url: str,
    collection_name: str,
    documents: Dict[str, str],
    run_id: str,
    metadata: Dict[str, str],
    ollama_client: Optional[OllamaClient] = None,
) -> None:
    """Store documents and metadata in ChromaDB."""

    host, port, ssl = _parse_chroma_url(chroma_url)
    client = chromadb.HttpClient(host=host, port=port, ssl=ssl)
    collection = client.get_or_create_collection(name=collection_name)

    ids = []
    docs = []
    metadatas = []
    embeddings = []

    for name, content in documents.items():
        ids.append(f"{run_id}:{name}")
        docs.append(content)
        item_meta = {"run_id": run_id, "name": name}
        item_meta.update(metadata)
        metadatas.append(item_meta)

        if ollama_client is not None:
            emb = ollama_client.embed(content)
            if emb is None:
                embeddings = []
                break
            embeddings.append(emb)

    if embeddings:
        collection.add(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)
    else:
        collection.add(ids=ids, documents=docs, metadatas=metadatas)
        if ollama_client is not None:
            logger.info("Stored without embeddings")
