"""Embed queries and retrieve text from an existing local Chroma collection."""

from typing import List

import chromadb
from chromadb.config import Settings
from chromadb.api.types import Document, Metadata, QueryResult
import numpy as np
import logging
import re

from app.docs_indexer.config import Config
from app.docs_indexer.embeddings.embeddings import EmbeddingClient, QUERY_PREFIXES

logger = logging.getLogger(__name__)

config = Config.from_env()
logger.info("Determining query prompt name...")
if (config.query_prompt_name in QUERY_PREFIXES):
    query_prefix = QUERY_PREFIXES[config.query_prompt_name]
else:
    logger.error(f"Unsupported QUERY_PROMPT_NAME: {config.query_prompt_name}")
    raise ValueError(f"Unsupported QUERY_PROMPT_NAME: {config.query_prompt_name}")
logger.info(f"Determined query prompt name: {config.query_prompt_name}")

embedding_client = EmbeddingClient(config)
collection = None


def embed_query(question: str) -> np.ndarray:
    """Return one query vector with the configured task prefix and dimensions."""
    # The shared client accepts prepared text, so apply the query prefix once.
    logger.info("Creating user query embedding...")
    logger.debug(f"User query: {question}")
    return embedding_client.encode([query_prefix + question])[0]


def retrieve_context(query_embedding: np.ndarray) -> tuple[str, str]:
    """Return prompt context and a matching source list for display in the answer."""
    global collection
    if collection is None:
        if not (config.chroma_path / "chroma.sqlite3").is_file():
            logger.error(f"No Chroma database at {config.chroma_path}")
            raise FileNotFoundError(f"No Chroma database at {config.chroma_path}")
        logger.debug(f"ChromaDB path: {config.chroma_path / "chroma.sqlite3"}")

        client = chromadb.PersistentClient(
            path=str(config.chroma_path),
            settings=Settings(),
        )
        collection = client.get_collection(
            name=config.collection_name,
            embedding_function=None,
        )

    count: int = collection.count()
    if count == 0:
        return "", ""
    results: QueryResult = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=min(config.retrieval_top_k, count),
        include=["documents", "metadatas"],
    )

    documents: List[Document] = results["documents"][0] if results["documents"] else []
    metadatas: List[Metadata] = results["metadatas"][0] if results["metadatas"] else []
    context_chunks = []
    sources = []

    for index, text in enumerate(documents):
        if (not text):
            continue
        
        metadata = {}
        if (index < len(metadatas)):
            metadata = metadatas[index] or {}

        source_details = []
        display_details = []

        for key, label in (
            ("title", "Title"),
            ("section", "Section"),
            ("source", "Source"),
            ("source_file", "File"),
            ("source_url", "URL"),
        ):
            value = str(metadata.get(key) or "").strip()
            if (not value):
                continue

            source_details.append(f"{label}: {value}")
            if (key == "source_url" and re.fullmatch(\
                r"https?://[^/\s<>]+(?:[/?#][^\s<>]*)?", value, re.IGNORECASE)):

                display_value = f"<{value}>"
            else:
                # Remove Markdown link formats such as "[something](something.com)"
                # and change them to "something"
                plain_value = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", value)
                plain_value = " ".join(plain_value.split()).replace(" > ", " → ")
                # Escape markdown special characters
                display_value = re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", plain_value)

            display_details.append(f"**{label}:** {display_value}")

        reference = f"[{index + 1}]"
        source_header = "\n".join([reference, *source_details])
        context_chunks.append(f"{source_header}\n\n{text}")
        
        if display_details:
            sources.append(f"- {reference} " + "\n\n  ".join(display_details))
        else:
            sources.append(f"- {reference} Source metadata unavailable")

    context = "\n\n---\n\n".join(context_chunks)
    source_list = "\n\n".join(sources)
    return context, source_list
