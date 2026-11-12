from __future__ import annotations

import hashlib
import json
import logging
from itertools import islice

import chromadb
from chromadb.api import ClientAPI
import numpy as np
from transformers import AutoTokenizer

from config import Config
from ingestion.chunker import MarkdownChunker
from ingestion.embed_documents import markdown_files_to_embed, read_markdown_file
from embeddings.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)

def main() -> None:
    """Creates an document index for ChromaDB."""

    config: Config = Config.from_env()

    for source, root in config.roots.items():
        if not root.is_dir():
            logger.error(f"File not found: {source}: {root}")
            raise FileNotFoundError(f"{source}: {root}")

    logger.info(f"Intializing Embedding Gemma 2's tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        config.tokenizer_id,
        local_files_only=True
    )
    chunker = MarkdownChunker(
        tokenizer=tokenizer,
        target=config.chunk_target_tokens,
        overlap=config.chunk_overlap_tokens,
        max_tokens=config.chunk_max_tokens
    )
    encoder = EmbeddingClient(config=config)

    logger.info("Creating ChromaDB client...")
    client: ClientAPI = chromadb.PersistentClient(path=str(config.chroma_path))
    try:
        logger.info("Creating ChromaDB collection...")
        collection: chromadb.Collection = client.create_collection(
            name=config.collection_name,
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}}
        )
        logger.info(f"Created ChromaDB collection with name: {config.collection_name}")
        config.build_metadata_path.unlink(missing_ok=True)

        files_seen: int = 0
        chunks_written: int = 0
        by_source: dict[str, int] = {}
        files = markdown_files_to_embed(config=config)

        # Check whether only a select number of files are to be parsed
        if (config.max_files > 0):
            logger.info(f"Will only parse the first {config.max_files} files...")
            files = islice(files, config.max_files)

        logger.info("Starting to process dataset...")
        for (source, path, relative) in files:
            files_seen += 1
            logger.info(f"Reading Markdown file: {source}/{relative}...")
            title, content = read_markdown_file(path=path)

            if not content:
                logger.info(f"No text content extracted from file: {source}/{relative}.\
                            Going to next file...")
                continue

            # Make sure the same passage isn't inserted twice
            seen_passages: set[str] = set()
            chunks = []

            logger.info(f"Chunking Markdown file: {source}/{relative}...")
            for (passage, hierarchy) in chunker.split(title=title, text=content):
                if passage not in seen_passages:
                    seen_passages.add(passage)
                    chunks.append((passage, hierarchy))

            logger.info(f"Processing chunks in batches of size {config.chroma_batch_size}")
            for start in range(0, len(chunks), config.chroma_batch_size):
                # Extract current batch
                batch = chunks[start:start + config.chroma_batch_size]

                # Extract the passage text from each chunk
                texts = [passage for passage, _ in batch]

                # Format each passage by concatenating the doc title and content
                inputs: list[str] = [f"title: {title} | text: {passage}" for passage in texts]

                logger.info(f"Generating embeddings for {source}/{relative}...")
                embeddings = encoder.encode(inputs)

                collection.add(
                    ids=[
                        hashlib.sha256(f"{source}/{relative}#{start + i}".encode()).hexdigest()
                        for i in range(len(batch))
                    ],
                    embeddings=embeddings.tolist(),
                    documents=texts,
                    metadatas=[
                        {
                            "source": source,
                            "source_file": relative,
                            "title": title,
                            "section": heading[:1000],
                        }
                        for _, heading in batch
                    ],
                )

                chunks_written += len(batch)
                by_source[source] = by_source.get(source, 0) + len(batch)

            if files_seen % 100 == 0:
                logger.info(f"Files: {files_seen:,} | chunks: {chunks_written:,}")

        if (chunks_written == 0 or collection.count() != chunks_written):
            logger.error("Index is empty or Chroma count differs from inserted chunks.")
            raise RuntimeError("Index is empty or Chroma count differs from inserted chunks.")

        logger.info("Writing post-embedding creation metrics...")
        config.build_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        config.build_metadata_path.write_text(json.dumps({
            "build_status": "complete",
            "embedding_backend": config.embedding_backend,
            "model_id": config.model_id,
            "model_revision": config.model_revision,
            "embedding_api_model": config.embedding_api_model if config.embedding_backend != "sentence_transformers" else None,
            "embedding_dimension": config.embedding_dimension,
            "normalize_embeddings": config.normalize_embeddings,
            "document_format": "title: {title} | text: {passage}",
            "query_prompt_name": config.query_prompt_name,
            "chroma_version": chromadb.__version__,
            "collection_name": config.collection_name,
            "distance": "cosine",
            "chunk_target_tokens": config.chunk_target_tokens,
            "chunk_max_tokens": config.chunk_max_tokens,
            "chunk_overlap_tokens": config.chunk_overlap_tokens,
            "source_files_scanned": files_seen,
            "chunks_in_database": chunks_written,
            "chunks_by_source": by_source,
            "partial_test": config.max_files != 0,
        }, indent=2) + "\n", encoding="utf-8")

        logger.info(f"Completed: {files_seen:,} files -> {chunks_written:,}\
                     vectors in {config.chroma_path}")

    finally:
        logger.info("Ending embeddings...")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    main()
